#include "services.h"
/* Register subset for MCPX USB startup and root-hub interrupts. All device
 * state belongs to the guest worker except the sampled pad presence flag. */
#include "ohci_boot.h"
#include "menu_gpu.h"
#include "frame_exchange.h"
#include "scanout.h"
#include "nv2a_boot.h"
#include "contiguous.h"
#include "runtime.h"
#include "guest_memory.h"
#include "usb/ohci.h"
#include "audio_boot.h"
#include <stdbool.h>
#ifdef NGB_PLAYER_BUILD
#include "recomp_settings.h"
static uint32_t settings_label;
static bool settings_confirm_held;
#endif
#include "usb/usb_gamepad.h"
#include <string.h>
#include <stdatomic.h>

enum {
    REVISION = 0x00, CONTROL = 0x04, COMMAND = 0x08, IRQ_STATUS = 0x0c,
    IRQ_ENABLE = 0x10, IRQ_DISABLE = 0x14, HCCA = 0x18,
    PERIOD_CURRENT = 0x1c, CONTROL_HEAD = 0x20, CONTROL_CURRENT = 0x24,
    BULK_HEAD = 0x28, BULK_CURRENT = 0x2c, DONE_HEAD = 0x30,
    INTERVAL = 0x34, PERIOD_START = 0x40, LS_THRESHOLD = 0x44,
    HUB_A = 0x48, HUB_B = 0x4c, HUB_STATUS = 0x50, PORT1 = 0x54, LAST_PORT = 0x60
};
static uint32_t regs[LAST_PORT / 4 + 1];

/* Only the UI thread samples libnx. All guest register changes belong to
 * the worker thread, including publishing a port attachment after startup. */
static atomic_bool pad_present;
static bool scanning_ports, start_reported;
static uint64_t frame_epoch;
static uint16_t frame_number;

void ngb_ohci_pad_present(int present)
{
    atomic_store(&pad_present, present != 0);
}

/* Endpoint zero is shared by the device's setup, data and status stages.
 * Keep the reply cursor across TDs: the default maximum packet size is 8. */
static UsbSetup setup;
static uint8_t reply[64];
static int reply_length, reply_position;
static bool setup_pending;
static uint8_t output_report[6];

static NgbExchange pad_samples = NGB_EXCHANGE_INIT;
static uint8_t reports[3][20] = {{0,20},{0,20},{0,20}};
static uint16_t previous_buttons;
/* Owned by the guest USB consumer. A held physical button retains the
 * assignment it had at press, even during a temporary game-state change. */
static uint8_t face_down, face_swapped;
static atomic_uint start_presses, movie_skip_edges;
unsigned ngb_movie_skip_edges(void) { return atomic_load(&movie_skip_edges); }
unsigned ngb_start_press_count(void) { return atomic_load(&start_presses); }
static atomic_bool menu_input;
static atomic_uint menu_edges;
static atomic_uint_fast64_t direction_ns;
static bool menu_drawn;
static unsigned menu_dpad, last_cursor, menu_flips, timing_reports;
static uint64_t menu_window_ns, change_ns, menu_entry_ns;
static unsigned menu_entry_frames;


/* Keep one physical Start edge through the warning's input lockout.
 * Count actual changes of guest front buffer, independently of UI speed. */
static atomic_bool start_edge;
static atomic_uint_fast64_t warning_press_ns;
uint64_t ngb_warning_start_time(void) { return atomic_load(&warning_press_ns); }
static bool warning_armed, warning_done, replay_start;
static unsigned replay_frames;

void ngb_warning_file_read(const char *name, int64_t offset)
{
    if (warning_done) return;
    if (!warning_armed) {
        warning_armed = !strcmp(name, "demo.afs") && offset == 0x151000;
    } else if (strcmp(name, "demo.afs") && strcmp(name, "sse.afs") && strcmp(name, "bgm.afs")) {
        warning_done = true;
        replay_start = false;
    }
}

void ngb_menu_draw(uint32_t cursor)
{
#ifdef NGB_PLAYER_BUILD
    if (!settings_label) {
        const char label[]="RECOMP SETTINGS";
        settings_label=ngb_contiguous_allocate(sizeof label,0,UINT32_MAX,4,4);
        if (settings_label) {
            memcpy((void*)ngb_guest_pointer(settings_label,sizeof label),label,sizeof label);
            /* Retail main menu text 0x90009, English and Japanese. */
            memcpy(ngb_fast_ram+0x43618c,&settings_label,4);
            memcpy(ngb_fast_ram+0x436190,&settings_label,4);
        }
    }
#endif
    if (!menu_entry_ns) menu_entry_ns=ngb_elapsed_ns();
    menu_drawn=true;
    if (cursor!=last_cursor) {
        change_ns=atomic_exchange(&direction_ns,0);
        last_cursor=cursor;
    }
}

/* Publish one directional state per guest frame. Preserve a short tap if
 * the user has already released it by the time the game checks its pad. */
static void sample_menu_frame(void)
{
    bool active=atomic_load(&menu_input);
    if (active!=menu_drawn) {
        atomic_exchange(&menu_edges,0);
        atomic_store(&direction_ns,0);
        atomic_store(&menu_input,menu_drawn);
        menu_window_ns=ngb_elapsed_ns();
        menu_flips=0;
        change_ns=0;
    }
    if (!menu_drawn) return;
    unsigned edges=atomic_exchange(&menu_edges,0);
    unsigned held=reports[ngb_latest(&pad_samples)][2]&15;
    menu_dpad=((held&3)?held&3:edges&3) | ((held&12)?held&12:edges&12);
    uint64_t now=ngb_elapsed_ns(), elapsed=now-menu_window_ns;
    char msg[112];
    if (change_ns && now>=change_ns) {
        snprintf(msg,sizeof(msg),"Main menu direction_to_flip_ms=%llu cursor=%u",
                 (unsigned long long)((now-change_ns)/1000000),last_cursor);
        ngb_kernel_log(msg);
        change_ns=0;
    }
    if (menu_entry_frames < 30 && ++menu_entry_frames == 30) {
        snprintf(msg,sizeof(msg),"Main menu entry first_30_flips_ms=%llu",
                 (unsigned long long)((now-menu_entry_ns)/1000000));
        ngb_kernel_log(msg);
    }
    ++menu_flips;
    if (elapsed>=3000000000ull) {
        if (timing_reports<8) {
            snprintf(msg,sizeof(msg),"Main menu flips=%u elapsed_ms=%llu",menu_flips,
                     (unsigned long long)(elapsed/1000000));
            ngb_kernel_log(msg);
            ngb_menu_gpu_report();
            ++timing_reports;
        }
        menu_window_ns=now; menu_flips=0;
    }
    menu_drawn=false;
}

void ngb_pad_flip(void)
{
    sample_menu_frame();
    if (!warning_armed || warning_done) return;
    if (atomic_exchange(&start_edge, false)) {
        replay_frames = 1;
        ngb_kernel_log("Buffered warning Start on guest flip");
    }
    if (!replay_frames) return;
    replay_start = ((replay_frames - 1) % 8) < 4;
    /* A cold install can spend hundreds of flips copying demo.afs before
     * the game begins checking Start. The next scene's read ends replay. */
    replay_frames = replay_frames % 8 + 1;
}

void ngb_ohci_pad_sample(uint16_t buttons, int16_t lx, int16_t ly, int16_t rx, int16_t ry)
{
    uint8_t *pad_report = reports[pad_samples.writer];
    if ((buttons & ~previous_buttons) & (16u | 256u))
        atomic_fetch_add(&movie_skip_edges,1);
    if ((buttons & 16) && !(previous_buttons & 16)) {
        atomic_fetch_add(&start_presses,1);
        if (ngb_scanout_ready() && !atomic_load(&warning_press_ns))
            atomic_store(&warning_press_ns,ngb_elapsed_ns());
        atomic_store(&start_edge, true);
    }
    unsigned directions=(buttons & ~previous_buttons) & 15;
    if (directions && atomic_load(&menu_input)) {
        atomic_store(&direction_ns,ngb_elapsed_ns());
        atomic_fetch_or(&menu_edges,directions);
    }
    previous_buttons=buttons;
    pad_report[2]=(uint8_t)buttons;
    for (unsigned i=0;i<8;i++) pad_report[4+i]=(buttons&(1u<<(8+i))) ? 255 : 0;
    const int16_t axes[4]={lx,ly,rx,ry};
    memcpy(pad_report+12,axes,sizeof(axes));
    ngb_publish(&pad_samples);
}

#ifdef NGB_PLAYER_BUILD
static atomic_bool quick_play;
extern int ngb_quick_controls_active(void);
void ngb_switch_sample_quick(unsigned raw){
    extern void ngb_switch_quick_pad(unsigned);
    static bool was_enabled;
    bool enabled=ngb_switch_setting(20)!=0;
    if(!enabled && !was_enabled)return;
    was_enabled=enabled;
    unsigned quick=0;
    if(enabled && (atomic_load(&quick_play) || ngb_quick_controls_active()))
        for(int i=0;i<6;i++)quick|=((raw>>ngb_switch_setting(78+i))&1u)<<i;
    ngb_switch_quick_pad(quick);
}
#endif
int usb_gamepad_report(int pad, uint8_t *out, int max)
{
    if (pad || max<20) return 0;
    memcpy(out,reports[ngb_latest(&pad_samples)],20);
    if (atomic_load(&menu_input)) out[2]=(out[2]&~15u)|menu_dpad;
#ifdef NGB_PLAYER_BUILD
    bool play=ngb_fast_ram && ngb_fast_ram[0x7F1B12]==1 && !ngb_fast_ram[0x7F1B11] &&
        !ngb_fast_ram[0xDB9AD5] && (ngb_fast_ram[0xDB9894]==2 || ngb_fast_ram[0xDB9894]==3) && !atomic_load(&menu_input);
    atomic_store(&quick_play,play);
    static bool chord_held;
    bool chord=(out[2]&96)==96; /* Minus + left stick: leave Start + Back available. */
    if(chord && !chord_held && ngb_fast_ram && ngb_fast_ram[0x7F1B12]==1 && !atomic_load(&menu_input)){
        chord_held=true;ngb_settings_open();memset(out+2,0,18);return 20;
    }
    chord_held=chord;
    extern int ngb_camera_first_person(void);
    unsigned raw=out[2];for(int i=0;i<8;i++)if(out[4+i])raw|=1u<<(8+i);
    if(!ngb_switch_setting(52) && (out[2]&32))out[2]&=~16u;
    static bool hud_held;
    bool hud=play && (raw&(1u<<ngb_switch_setting(84)));
    extern void ngb_switch_toggle_hud(void);
    if(hud && !hud_held)ngb_switch_toggle_hud();
    hud_held=hud;
    if(ngb_quick_controls_active()){memset(out+2,0,18);return 20;}
    if(play){
        unsigned bits=out[2],mapped=0;
        for(int i=0;i<8;i++)if(out[4+i])bits|=1u<<(8+i);
        for(int i=0;i<16;i++)mapped|=((bits>>ngb_switch_setting(60+i))&1u)<<i;
        if(bits&(1u<<ngb_switch_setting(76)))mapped|=(1u<<8)|(1u<<10);
        if(bits&(1u<<ngb_switch_setting(77)))mapped|=(1u<<9)|(1u<<11);
        out[2]=mapped;for(int i=0;i<8;i++)out[4+i]=(mapped&(1u<<(8+i)))?255:0;
        int fp=ngb_camera_first_person(),pct=ngb_switch_setting(47);
        for(int i=0;i<2;i++){int16_t v;memcpy(&v,out+16+2*i,2);
            int axis=pct<100?v*pct/100:v;
            if(ngb_switch_setting((fp?48:50)+i))axis=axis==-32768?32767:-axis;
            v=axis;memcpy(out+16+2*i,&v,2);}
    }
    bool confirm=out[4] || (out[2]&16) || out[6];
    bool pressed_confirm=confirm && !settings_confirm_held;
    settings_confirm_held=confirm;
    if (pressed_confirm && settings_label && atomic_load(&menu_input) && last_cursor==3) {
        ngb_settings_open();
        memset(out+2,0,18);
        return 20;
    }
#endif
    /* Use the game state on the guest worker, after loading system.dat.
     * Xbox reports retain their native lettering in the front end and pause
     * screens. Flip the four analog button bytes only in active play. */
    unsigned held=0;
    for(unsigned i=0;i<4;i++) if(out[4+i]) held|=1u<<i;
    unsigned pressed=held & ~face_down;
    face_swapped &= held;
    if (pressed && ngb_fast_ram && ngb_fast_ram[0x7F1B12]==1 && !ngb_fast_ram[0x7F1B11] &&
        !ngb_fast_ram[0xDB9AD5] && (ngb_fast_ram[0xDB9894]==2 || ngb_fast_ram[0xDB9894]==3) &&
        !atomic_load(&menu_input)) face_swapped |= pressed;
    face_down=held;
    unsigned routed=(held & ~face_swapped) | ((face_swapped&5)<<1) | ((face_swapped&10)>>1);
    for(unsigned i=0;i<4;i++) out[4+i]=(routed&(1u<<i))?255:0;
    if (replay_start) out[2] |= 16;
    return 20;
}

static unsigned control_stage(uint32_t *td)
{
    uint32_t start=td[1], end=td[3];
    if (start && (end<start || end-start>=8192 ||
                  (end>>12)>(start>>12)+1))
        ngb_stop("unsupported OHCI TD pages", start);
    unsigned size=start ? end-start+1 : 0;
    unsigned pid=(td[0]>>19)&3;
    unsigned moved=0;
    if (pid==0) {
        if (size!=sizeof(setup)) ngb_stop("invalid USB setup packet", size);
        memcpy(&setup,ngb_dma_pointer(start,size),size);
        setup_pending=true;
        reply_length=-1;
        reply_position=0;
        moved=size;
        char line[100];
        snprintf(line,sizeof(line),"OHCI0 SETUP request=%02x:%02x value=%04x length=%u",
                 setup.bmRequestType,setup.bRequest,setup.wValue,setup.wLength);
        ngb_kernel_log(line);
    } else if (!setup_pending) {
        ngb_stop("USB stage without SETUP", pid);
    } else if (pid==2) {
        if (reply_length<0) {
            reply_length=usb_gamepad_control(0,&setup,reply,sizeof(reply));
            if (reply_length<0) { setup_pending=false; return 4; } /* STALL */
        }
        moved=(unsigned)(reply_length-reply_position);
        if (moved>size) moved=size;
        if (moved) memcpy(ngb_dma_pointer(start,moved),reply+reply_position,moved);
        reply_position+=moved;
        if (!size) setup_pending=false;
    } else if (pid==1 && size && setup.bmRequestType==0x21 && setup.bRequest==9 &&
               setup.wValue==0x200 && !setup.wIndex && setup.wLength==sizeof(output_report)) {
        if (size>sizeof(output_report)-(unsigned)reply_position) return 4;
        memcpy(output_report+reply_position,ngb_dma_pointer(start,size),size);
        reply_position+=size;
        moved=size;
        if (reply_position==(int)sizeof(output_report)) {
            if (output_report[0] || output_report[1]!=6) return 4;
            reply_length=reply_position=0;
        }
    } else if (pid==1 && !size) {
        setup_pending=false;
    } else ngb_stop("unsupported USB control OUT",size);
    td[1]=moved==size ? 0 : start+moved;
    return 0;
}

/* The interrupt pipe delivers XID reports after control enumeration. */
static unsigned interrupt_stage(uint32_t ed, uint32_t *td)
{
    unsigned endpoint = (ed >> 7) & 15;
    unsigned direction = (ed >> 11) & 3;
    if (!direction) direction = (td[0] >> 19) & 3;
    if ((ed & (1u << 15)) || (direction == 2 ? endpoint != 1 : endpoint != 2)) ngb_stop("unsupported USB interrupt endpoint", ed);
    uint32_t start = td[1], end = td[3];
    if (!start || end < start || end-start >= 8192 || (end>>12) > (start>>12)+1)
        ngb_stop("unsupported OHCI interrupt buffer", start);
    unsigned length = end-start+1, moved;
    if (direction == 2) {
        uint8_t report[20];
        moved = usb_gamepad_report(0, report, sizeof(report));
        if (moved > length) moved = length;
        if (moved >= 3 && (report[2]&16) && !start_reported) {
            ngb_kernel_log("First Start report delivered");
            start_reported = true;
        }
        memcpy(ngb_dma_pointer(start,moved),report,moved);
    } else if (direction == 1 && length == sizeof(output_report)) {
        memcpy(output_report,ngb_dma_pointer(start,length),length);
        if (output_report[0] || output_report[1] != length) return 4;
        moved = length;
    } else return 4;
    td[1] = moved == length ? 0 : start + moved;
    return moved < length && !(td[0] & (1u << 18)) ? 9 : 0;
}

static void walk_endpoints(uint32_t addr, int periodic, uint32_t *done)
{
    unsigned descriptors=0;
    while (addr) {
        if (++descriptors>256) ngb_stop("cyclic OHCI control list",addr);
        uint32_t *ed=ngb_dma_pointer(addr,16);
        while (!(ed[0]&(1u<<14)) && !(ed[2]&1) && ((ed[2]^ed[1])&~15u)) {
            if (++descriptors>256) ngb_stop("cyclic OHCI transfer list",ed[2]);

            if (!periodic && ((ed[0]>>7)&15)) ngb_stop("nonzero USB control endpoint",ed[0]);
            uint32_t head=ed[2]&~15u;
            uint32_t *td=ngb_dma_pointer(head,16);
            uint32_t next=td[2]&~15u;
            uint32_t carry=ed[2]&2;
            unsigned condition=5; /* device not responding */
            if ((regs[PORT1/4]&3)==3 && (ed[0]&127)==usb_gamepad_address(0)) {
                unsigned packet_size=(ed[0]>>16)&0x7ff;
                if (!packet_size) ngb_stop("zero OHCI control packet size",ed[0]);
                uint32_t initial=td[1];
                condition=periodic ? interrupt_stage(ed[0],td) : control_stage(td);
                if (!condition) {
                    unsigned count=!initial ? 0 : (td[1] ? td[1]-initial : td[3]+1-initial);
                    unsigned packets=count ? (count+packet_size-1)/packet_size : 1;
                    unsigned toggle=(td[0]>>24)&3;
                    if (toggle&2) carry=(toggle&1)<<1;
                    carry^=(packets&1)<<1;
                }
            }
            td[0]=(td[0]&0x0fffffff)|(condition<<28);
            td[2]=*done;
            *done=head;
            ed[2]=next | carry | (condition!=0);
        }
        addr=ed[3]&~15u;
    }
}

/* Control and interrupt completions belong to the same guest-owned chain. */
static void run_lists(uint32_t hcca, uint64_t frames)
{
    if ((regs[CONTROL/4]&0x20) && (regs[COMMAND/4]&4)) {
        unsigned count=0;
        for (uint32_t addr=regs[BULK_HEAD/4];addr;) {
            if (++count>256) ngb_stop("cyclic OHCI bulk list", addr);
            uint32_t *ed=ngb_dma_pointer(addr,16);
            if (!(ed[0]&(1u<<14)) && !(ed[2]&1) && ((ed[1]^ed[2])&~15u))
                ngb_stop("unsupported OHCI bulk transfer",addr);
            addr=ed[3]&~15u;
        }
        regs[COMMAND/4]&=~4u;
    }
    if (regs[IRQ_STATUS/4]&2) return;
    uint32_t done = 0;
    if (regs[CONTROL/4]&4) {
        unsigned slots = frames < 32 ? (unsigned)frames : 32;
        const uint32_t *table = ngb_dma_pointer(hcca,128);
        for (unsigned back = slots; back; --back)
            walk_endpoints(table[(frame_number + 1u - back)&31] & ~15u,1,&done);
    }
    if ((regs[CONTROL/4]&0x10) && (regs[COMMAND/4]&2)) {
        walk_endpoints(regs[CONTROL_HEAD/4],0,&done);
        regs[COMMAND/4]&=~2u;
    }
    if (done) {
        uint32_t *published=ngb_dma_pointer(hcca+0x84,4);
        *published=done | ((regs[IRQ_STATUS/4]&regs[IRQ_ENABLE/4]&0x7d)!=0);
        regs[IRQ_STATUS/4]|=2;
        ngb_kernel_log("OHCI0 published control completion");
    }
}

uint32_t ngb_ohci_irq_pending(void)
{
    uint32_t enabled = regs[IRQ_ENABLE / 4];
    if ((regs[CONTROL / 4] & 0xc0) == 0x80) {
        uint64_t now = ngb_elapsed_ns(), frames = (now - frame_epoch) / 1000000;
        if (frames) {
            frame_epoch += frames * 1000000;
            if ((frame_number & 0x7fff) + frames >= 0x8000) regs[IRQ_STATUS / 4] |= 0x20;
            frame_number += (uint16_t)frames;
            regs[IRQ_STATUS / 4] |= 4;
            uint32_t hcca = regs[HCCA / 4];
            if (hcca) {
                void *dst = ngb_contiguous_pointer(0x80000000u + hcca + 0x80, 2);
                if (!dst) ngb_stop("unmapped OHCI frame number", hcca);
                memcpy(dst, &frame_number, 2);
                run_lists(hcca,frames);
            }
        }
    }
    if (scanning_ports && (regs[CONTROL / 4] & 0xc0) == 0x80) {
        uint32_t *port = &regs[PORT1 / 4];
        bool present = atomic_load(&pad_present);
        if (present != ((*port & 1) != 0)) {
            if (present) *port |= 1;
            else *port &= ~3u;
            *port |= 1u << 16; /* ConnectStatusChange */
            regs[IRQ_STATUS / 4] |= 0x40;
            ngb_kernel_log(present ? "OHCI0 port 1 connected" : "OHCI0 port 1 disconnected");
        }
    }
    return (enabled & 0x80000000u) ? regs[IRQ_STATUS / 4] & enabled : 0;
}

void ngb_ohci_reset(void)
{
#ifdef NGB_PLAYER_BUILD
    settings_label=0;
    settings_confirm_held=false;
#endif
    face_down=face_swapped=0;
    start_reported=false;
    atomic_store(&menu_input,false);
    atomic_store(&menu_edges,0);
    atomic_store(&direction_ns,0);
    menu_dpad=menu_flips=timing_reports=menu_entry_frames=0;
    menu_entry_ns=0;
    last_cursor=UINT32_MAX;
    menu_drawn=false;
    change_ns=0;
    atomic_store(&warning_press_ns,0);
    warning_armed = warning_done = replay_start = false;
    replay_frames = 0;
    atomic_store(&start_edge, false);
    memset(regs, 0, sizeof(regs));
    setup_pending = false;
    usb_gamepad_reset(0);
    scanning_ports = false;
    frame_number = 0;
    regs[PORT1 / 4] = regs[PORT1 / 4 + 1] = 0x100; /* powered */
    regs[REVISION / 4] = 0x10;
    regs[INTERVAL / 4] = 0x27782edf;
    regs[LS_THRESHOLD / 4] = 0x628;
    regs[HUB_A / 4] = 0x202; /* Two downstream ports, no power switching. */
}

static void trace(const char *operation, uint32_t offset, uint32_t value)
{
    if (!ngb_mmio_trace_enabled()) return;
    char message[96];
    snprintf(message, sizeof(message), "OHCI0 %s offset=%02x value=%08x", operation, offset, value);
    ngb_kernel_log(message);
}

uint32_t ngb_bus_read32(uint32_t va)
{
    if (ngb_nv2a_contains(va)) return ngb_nv2a_read32(va);
    uint32_t offset = va - XBOX_OHCI0_BASE, value;
    if (va-0xfec00000u < 4096) return ngb_ac97_read(va,4);
    if (va-0xfe800000u < 0x80000) return ngb_apu_read(va);
    if (offset >= XBOX_OHCI_SIZE) {
        memcpy(&value, (const void *)ngb_guest_scalar(va, sizeof(value)), sizeof(value));
        return value;
    }
    switch (offset) {
    case IRQ_DISABLE:
        return regs[IRQ_ENABLE / 4];
    case IRQ_STATUS: case IRQ_ENABLE:
    case PORT1: case PORT1 + 4: case PORT1 + 8: case LAST_PORT:
    case REVISION: case CONTROL: case COMMAND: case HCCA: case PERIOD_CURRENT:
    case CONTROL_HEAD: case CONTROL_CURRENT: case BULK_HEAD: case BULK_CURRENT:
    case DONE_HEAD: case INTERVAL: case PERIOD_START: case LS_THRESHOLD:
    case HUB_A: case HUB_B: case HUB_STATUS:
        value = regs[offset / 4];
        trace("read", offset, value);
        return value;
    default: ngb_stop("unsupported OHCI read", va);
    }
}

void ngb_bus_write32(uint32_t va, uint32_t value)
{
    if (ngb_nv2a_contains(va)) {
        ngb_nv2a_write32(va, value);
        return;
    }
    uint32_t offset = va - XBOX_OHCI0_BASE;
    if (va-0xfec00000u < 4096) { ngb_ac97_write(va,4,value); return; }
    if (va-0xfe800000u < 0x80000) { ngb_apu_write(va,value); return; }
    if (offset >= XBOX_OHCI_SIZE) {
        memcpy((void *)ngb_guest_scalar(va, 4), &value, 4);
        return;
    }
    trace("write", offset, value);
    switch (offset) {
    case IRQ_STATUS:
        regs[IRQ_STATUS / 4] &= ~value; /* write one to acknowledge */
        return;
    case IRQ_ENABLE:
        regs[IRQ_ENABLE / 4] |= value & 0xc000007fu;
        if (value & 0x40) scanning_ports = true;
        return;
    case IRQ_DISABLE:
        regs[IRQ_ENABLE / 4] &= ~value;
        return;
    case PORT1: case PORT1 + 4: case PORT1 + 8: case LAST_PORT:
        if (offset > PORT1 + 4) return; /* driver scans four slots */
        /* Only defined bits issue commands. The XDK can leave the upper
         * half of a stack word (including reserved bit 31) in the write. */
        if (value & 0x0cu) ngb_stop("unsupported OHCI port suspend/resume", value);
        regs[offset / 4] &= ~(value & 0x001f0000u);
        if (value & 0x100) regs[offset / 4] |= 0x100;
        if (value & 0x200) regs[offset / 4] &= ~0x100u;
        if (value & 1) regs[offset / 4] &= ~2u;
        if ((value & 2) && (regs[offset / 4] & 1)) regs[offset / 4] |= 2;
        if ((value & 0x10) && (regs[offset / 4] & 1)) {
            usb_gamepad_reset(0);
            setup_pending=false;
            regs[offset / 4] |= 2 | (1u << 20);
            regs[IRQ_STATUS / 4] |= 0x40;
        }
        return;
    case COMMAND:
        if (value == 1) {
            /* HCR self-clears. Root-hub policy survives this software reset. */
            frame_number = 0;
            uint32_t routing = regs[CONTROL / 4] & (1u << 8);
            memset(regs + CONTROL / 4, 0, INTERVAL - CONTROL);
            scanning_ports = false;
            regs[IRQ_ENABLE / 4] = 0x80000000u;
            regs[CONTROL / 4] = routing | 0xc0; /* USB suspend after HCR */
            regs[INTERVAL / 4] = 0x27782edf;
            regs[PERIOD_START / 4] = 0;
            regs[LS_THRESHOLD / 4] = 0x628;
        } else if (!(value & ~6u)) regs[COMMAND/4] |= value;
        else if (value) ngb_stop("unsupported OHCI command", value);
        return;
    case HCCA:
        if (value && ((value & 255) || value >= 0x08000000u ||
                      !ngb_contiguous_pointer(0x80000000u + value, 256)))
            ngb_stop("unmapped OHCI HCCA", value);
        break;
    case CONTROL:
        if ((regs[offset / 4] & 0xc0) != 0x80 && (value & 0xc0) == 0x80)
            frame_epoch = ngb_elapsed_ns();
        value &= 0x7ff; break;
    case CONTROL_HEAD: case CONTROL_CURRENT: case BULK_HEAD: case BULK_CURRENT:
        value &= ~15u; break;
    case LS_THRESHOLD: value &= 0xfff; break;
    case PERIOD_START: value &= 0x3fff; break;
    case INTERVAL: case HUB_B: break;
    case HUB_A: value = (value & 0xff001f00u) | 2; break;
    case HUB_STATUS:
        /* The startup write clears DeviceRemoteWakeupEnable. */
        if (value & ~0x80000000u) ngb_stop("unsupported OHCI root hub command", value);
        if (value) regs[offset / 4] &= ~(1u << 15);
        return;
    case REVISION: case PERIOD_CURRENT: case DONE_HEAD: return;
    default: ngb_stop("unsupported OHCI write", va);
    }
    regs[offset / 4] = value;
}
