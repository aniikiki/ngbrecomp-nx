/* Early host-independent boot adapter. Unimplemented services stop execution;
 * they never report success or silently skip the guest's work. */
#define _POSIX_C_SOURCE 200809L
#ifdef __SWITCH__
#include "switch_guest_regs.h"
#endif
#ifdef NGB_DIRECT3D
#include "direct/output.h"
#endif
#include "runtime.h"
#include "profile.h"
#include "menu_gpu.h"
#include "scanout.h"
#include "recomp_funcs.h"
#include "ngb_image.h"
#include "vm.h"
#include "contiguous.h"
#include "scene.h"
#include "ohci_boot.h"
#include "nv2a_boot.h"
#include "services.h"
#include "timers.h"
#include "files.h"
#include "files_bridge.h"
#include <stdatomic.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdarg.h>
#include <time.h>
#ifdef __SWITCH__
#include <switch/arm/counter.h>
#endif

/* Cold cache installation and the opening sequence span multiple scenes. */
#define BOOT_BUDGET_NS 180000000000ull
#define RAM_BYTES NGB_RAM_BYTES
#define GUEST_TICK_COUNT NGB_TICK_COUNT
#define BOOT_STACK_TOP 0x03fff000u
#define THUNK_BASE 0xfe000000u

#ifdef __SWITCH__
RecompRegs g_regs;
#else
RECOMP_TLS RecompRegs g_regs;
#endif
ptrdiff_t g_xbox_mem_offset;
uint32_t g_xbox_code_lo, g_xbox_code_hi, g_recomp_capture_va;
int g_force_return;
volatile uint32_t g_icall_trace[16], g_icall_trace_idx;
volatile uint64_t g_icall_count, g_icall_guard_hits, g_icall_guard_misses;

static unsigned char *ram;
/* Image sections stay resident for the boot. The USB driver passes a buffer
 * inside image BSS to MmLockUnlockBufferPages during enumeration. */
static int trap_null;
static uint8_t image_resident[RAM_BYTES/4096];
static uint16_t image_pins[RAM_BYTES/4096];
static int pin_image(uint32_t va, uint32_t bytes, int unlock)
{
    if (!bytes || va>=RAM_BYTES || bytes>RAM_BYTES-va) return 0;
    unsigned first=va/4096, last=(va+bytes-1)/4096;
    for (unsigned i=first;i<=last;i++)
        if (!image_resident[i] || (unlock ? !image_pins[i] : image_pins[i]==UINT16_MAX)) return 0;
    for (unsigned i=first;i<=last;i++) image_pins[i]+=unlock ? -1 : 1;
    return 1;
}
/* The XDK input driver carves small objects from physical page zero. */
static _Alignas(16) unsigned char physical_page_zero[4096];
static uint16_t page_zero_pins;
static _Alignas(16) unsigned char kernel_page[4096];
static FILE *boot_log;
static jmp_buf stop_context;
static atomic_bool cancel;
static int stopped_status;
static char stopped_reason[256];
#ifdef NGB_REGISTER_PACKAGE
/* Referenced by the candidate's ARM checkpoint, on the single guest thread. */
#define current_va ngb_reg_current_va
#define recent ngb_reg_recent
#define entries ngb_reg_entries
__attribute__((visibility("hidden"))) uint32_t current_va, recent[32];
__attribute__((visibility("hidden"))) uint64_t entries;
#else
static uint32_t current_va, recent[32];
static uint64_t entries;
#endif
static uint32_t thunk_ordinals[512], pending_ordinal;
static uint64_t start_ns;
/* Zero once the game reaches its interactive title, where the player may wait indefinitely. */
static uint64_t startup_deadline;
uint64_t ngb_guest_polls;
unsigned ngb_poll_mask = 3;
static int reported_contiguous_access;
static uint32_t menu_cursor;
static uint32_t flicker_filter, luma_filter, saved_av_data;
static unsigned thunk_count, thread_count;
/* A pool block owns a separate committed VM reservation. Keep its original
 * size for ExQueryPoolBlockSize and only allow freeing live pool blocks. */
static uint32_t pool_sizes[(NGB_VM_END-NGB_VM_BEGIN)/4096];
static atomic_uint log_lines;
static unsigned syscall_seen[512];
static struct { uint32_t address, depth, owner; } locks[64];
static uint32_t shutdown_registrations[32];
static int delivering_callback;
static bool interrupt_enabled = true;
static uint32_t usb_interrupt, gpu_interrupt, apu_interrupt, ac97_interrupt, dpc_queue[32];
unsigned ngb_pending_dpcs;
static void poll_callbacks(void);
static void yield_worker(void);
static void report_workers(void);
static void fire_timer(uint32_t address, uint32_t dpc, int periodic);
extern size_t recomp_get_count(void);

static uint64_t now_ns(void)
{
#ifdef __SWITCH__
    return armTicksToNs(armGetSystemTick());
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000u + ts.tv_nsec;
#endif
}

static int startup_expired(void) { return startup_deadline && now_ns() >= startup_deadline; }

uint64_t ngb_elapsed_ns(void) { return now_ns() - start_ns; }

#ifdef __SWITCH__
int ngb_mmio_trace_enabled(void) { return boot_log && log_lines < 2048; }
#endif

static void note(const char *format, ...)
{
    if (!boot_log) return;
    unsigned line_limit=2048;
#ifndef __SWITCH__
    if (getenv("NGB_FULL_TRACE")) line_limit=1000000;
#endif
    if (log_lines++ >= line_limit && strncmp(format, "[STOP]", 6) &&
        strncmp(format, "[RESULT]", 8) && (ngb_scene_active || strncmp(format, "[MEMORY] protect ", 17)) && strncmp(format, "[REGS]", 6) &&
        strncmp(format, "[RECENT]", 8) && strncmp(format, "[THREAD] id=", 12)) return;
    va_list ap;
    va_start(ap, format);
    vfprintf(boot_log, format, ap);
    va_end(ap);
    fputc('\n', boot_log);
    if (!(log_lines % 32) || !strncmp(format, "[STOP]", 6) || !strncmp(format, "[RESULT]", 8))
        fflush(boot_log);
}

_Noreturn void ngb_stop(const char *reason, uint32_t detail)
{
#ifdef NGB_DIRECT3D
    ngb_direct_check_stop(reason, detail);
#endif
    report_workers();
    snprintf(stopped_reason, sizeof(stopped_reason), "%s: 0x%08x", reason, detail);
    note("[STOP] %s; function=%08x esp=%08x entries=%llu icalls=%llu",
         stopped_reason, current_va, g_esp, (unsigned long long)entries,
         (unsigned long long)g_icall_count);
    note("[REGS] eax=%08x ebx=%08x ecx=%08x edx=%08x esi=%08x edi=%08x fs=%08x",
         g_eax, g_ebx, g_ecx, g_edx, g_esi, g_edi, g_fs_base);
    unsigned n = entries < 32 ? (unsigned)entries : 32;
    for (unsigned i = 0; i < n; ++i)
        note("[RECENT] %08x", recent[(entries - n + i) % 32]);
    longjmp(stop_context, 1);
}

void ngb_device_return(uint32_t result)
{
    note("[D3D] CreateDevice returned HRESULT=%08x", result);
}

static void checkpoint_event(uint32_t va)
{
    if (va == 0x0017a010u && MEM32(g_ebx + 4) == 8) {
        uint32_t cursor = MEM32(g_ebx + 0x54);
        if (menu_cursor == UINT32_MAX) {
            startup_deadline = 0;
            ngb_menu_gpu_enable();
#ifdef __SWITCH__
            extern void ngb_frontend_menu_controls(void);
            ngb_frontend_menu_controls();
#endif
        }
#ifdef NGB_PLAYER_BUILD
        extern void ngb_switch_sync_settings(void);
        ngb_switch_sync_settings();
        /* Refresh cached rows using the retail flag lookup, including earned flags
         * when a temporary unlock is switched off. Never edit system.dat. */
        static int previous[3]={-1,-1,-1};
        const unsigned row[]={2,4,5};uint32_t list=MEM32(g_ebx);
        for(unsigned i=0;i<3;i++){
            extern int ngb_switch_setting(unsigned);
            int on=ngb_switch_setting(26+i);
            if(on!=previous[i] && (on || previous[i]>=0)){
                uint32_t e=list+row[i]*8,flag=MEM32(e);
                if(flag==10+i){
                    uint32_t a=g_eax,c=g_ecx;g_ecx=flag;PUSH32(g_esp,0);sub_001DB520();
                    MEM8(e+4)=MEM8(e+5)=(g_eax&255)!=0;g_eax=a;g_ecx=c;
                }
            }
            previous[i]=on;
        }
#endif
        ngb_menu_draw(cursor);
        if (menu_cursor != cursor) {
            char line[80];
            snprintf(line, sizeof(line), "Main menu cursor=%u", cursor);
            ngb_kernel_log(line);
            menu_cursor = cursor;
        }
    }
    if (va == 0x0031dc50u) {
        startup_deadline = 0;
        ngb_kernel_log("Opening movie guest teardown");
        ngb_menu_gpu_prepare();
    }
    if (va == 0x003cc310u) note("[D3D] Direct3D_CreateDevice entry=%08x", va);
    if (entries <= 48) note("[ENTER] %08x", va);
}

void ngb_checkpoint(uint32_t va)
{
    current_va = va;
    recent[entries++ % 32] = va;
    if (__builtin_expect(entries <= 48 || va == 0x0017a010u || va == 0x0031dc50u || va == 0x003cc310u, 0))
        checkpoint_event(va);
    // The shared poll checks cancellation and the boot deadline every 256 tickets,
    // including tight loops that never reach another function entry.
    ngb_guest_block_poll();
}

void ngb_poll_due(uint64_t ticket)
{
    if (interrupt_enabled && !delivering_callback && (usb_interrupt || gpu_interrupt || apu_interrupt || ac97_interrupt || ngb_pending_dpcs)) poll_callbacks();
    if ((ticket & 255u) != 0) return;
    ngb_audio_poll();
    yield_worker();
    if (atomic_load(&cancel)) {
        stopped_status = NGB_BOOT_CANCELLED;
        ngb_stop("cancel requested", current_va);
    }
    if (startup_expired())
        ngb_stop("bootstrap time budget reached", current_va);
    if (interrupt_enabled && !delivering_callback && MEM8(g_fs_base + 0x24) < 2) {
        delivering_callback = 1;
        ngb_timers_poll(now_ns() / 100, fire_timer);
        delivering_callback = 0;
    }
}

static void poll_runtime(bool waiting)
{
    if (waiting) ngb_poll_due(++ngb_guest_polls);
    else ngb_guest_block_poll();
}

void ngb_poll(void) { ngb_guest_block_poll(); }

static inline void *contiguous_page(uint32_t va, size_t span)
{
    uint32_t physical = va - 0x80000000u;
    if (ngb_scene_active && physical < 0x08000000u) {
        unsigned page = physical >> 12, offset_in_page = physical & 4095;
        uint8_t *base = ngb_contiguous_pages[page];
        if (base && span <= 4096 - offset_in_page && !ngb_target_pages[page]) {
            ngb_vertex_dirty[page] = ngb_texture_dirty[page] = 1;
            return base + offset_in_page;
        }
    }
    return NULL;
}

void *ngb_guest_high_vector(uint32_t address)
{
    return contiguous_page(address, 16);
}

void ngb_vector_read_slow(uint32_t address, uint32_t lanes[4])
{
    const void *page = ngb_guest_vector_page(address);
    if (page) memcpy(lanes, page, 16);
    else for (unsigned i = 0; i < 4; ++i) lanes[i] = MEM32(address + 4 * i);
}

void ngb_vector_write_slow(uint32_t address, const uint32_t lanes[4])
{
    void *page = ngb_guest_vector_page(address);
    if (page) memcpy(page, lanes, 16);
    else for (unsigned i = 0; i < 4; ++i) MEM32(address + 4 * i) = lanes[i];
}

uintptr_t ngb_guest_scalar_fallback(uint32_t address, size_t bytes)
{
    return ngb_guest_scalar_paged(address, bytes);
}

uintptr_t ngb_guest_pointer(uint32_t va, size_t bytes)
{
    uint32_t offset = va;
    /* Zero-count REP can point one byte past the last mapped page. */
    if (ram && !bytes) return (uintptr_t)ram;
    if (va < RAM_BYTES) {
        if (!ram || (trap_null && offset < 0x1000) || bytes > RAM_BYTES - offset)
            ngb_stop("unmapped guest address / MMIO", va);
        if (offset < NGB_VM_END && (uint64_t)offset + bytes > NGB_VM_BEGIN &&
            !ngb_vm_access(offset, bytes)) ngb_stop("uncommitted guest allocation", va);
        if (offset >= GUEST_TICK_COUNT && offset < GUEST_TICK_COUNT + 4) {
            uint32_t elapsed_ms = (uint32_t)((now_ns() - start_ns) / 1000000);
            memcpy(ram + GUEST_TICK_COUNT, &elapsed_ms, sizeof(elapsed_ms));
        }
        return (uintptr_t)(ram + offset);
    }
    void *direct = contiguous_page(va, bytes == 1 ? 8 : bytes);
    if (direct) return (uintptr_t)direct;
    if (va >= 0x80010000u && va < 0x80011000u && bytes <= 0x80011000u - va)
        return (uintptr_t)(kernel_page + (va - 0x80010000u));
    if (va >= 0x80000000u && va < 0x80001000u && bytes <= 0x80001000u - va)
        return (uintptr_t)(physical_page_zero + (va - 0x80000000u));
    if (ngb_contiguous_in_pool(va)) {
        void *pointer = ngb_contiguous_pointer(va, bytes);
        if (!pointer) ngb_stop("unallocated contiguous memory", va);
        if (!reported_contiguous_access && bytes) {
            note("[MEMORY] first guest access va=%08x bytes=%zu function=%08x", va, bytes, current_va);
            reported_contiguous_access = 1;
        }
        return (uintptr_t)pointer;
    }
    if (ngb_nv2a_contains(va)) {
        void *pointer = ngb_instance_aperture(va, bytes);
        if (pointer) return (uintptr_t)pointer;
        ngb_stop("unhandled NV2A guest access", va);
    }
    if (va>>16==0xfe83 || va>>16==0xfe85) {
        void *p=ngb_dsp_memory(va,bytes);
        if (p) return (uintptr_t)p;
    }
    if (va >= THUNK_BASE && (va - THUNK_BASE) / 4 < thunk_count)
        ngb_stop(ngb_kernel_name(thunk_ordinals[(va - THUNK_BASE) / 4]), va);
    ngb_stop("unmapped guest address / MMIO", va);
}

void *ngb_dma_pointer(uint32_t address, size_t size)
{
    if (!address || address >= 0x08000000 || size > 0x08000000u-address)
        ngb_stop("invalid guest DMA range", address);
    if (address < 4096 || address >= 0x04000000)
        address += 0x80000000u;
    return (void *)ngb_guest_pointer(address,size);
}

static uint32_t read32(uint32_t va)
{
    uint32_t value;
    memcpy(&value, (void *)ngb_guest_scalar(va, 4), 4);
    return value;
}
static void write32(uint32_t va, uint32_t value)
{
    memcpy((void *)ngb_guest_scalar(va, 4), &value, 4);
}
static uint32_t arg(unsigned index) { return read32(g_esp + 4 + index * 4); }

static uint32_t run_callback(uint32_t routine, uint8_t irql, const uint32_t *args, unsigned count)
{
    recomp_func_t fn = recomp_lookup(routine);
    if (!fn) ngb_stop("unresolved interrupt or DPC routine", routine);
    uint32_t saved_ordinal = pending_ordinal;
    bool saved_if = interrupt_enabled;
    RecompRegs saved = g_regs;
    uint32_t saved_va = current_va;
    /* Dedicated stack/SEH chain; never overwrite the interrupted guest frame. */
    memcpy((void *)ngb_guest_pointer(0x4400, 0x100),
           (void *)ngb_guest_pointer(g_fs_base, 0x100), 0x100);
    g_fs_base = 0x4400;
    MEM8(g_fs_base + 0x24) = irql;
    write32(g_fs_base, 0xffffffff);
    write32(g_fs_base + 0x18, g_fs_base);
    write32(g_fs_base + 8, 0x03ee0000);
    g_esp = 0x03eff000;
    for (unsigned i = count; i; --i) PUSH32(g_esp, args[i - 1]);
    PUSH32(g_esp, 0);
    fn();
    if (g_esp != 0x03eff000) ngb_stop("unbalanced guest callback stack", routine);
    uint32_t result = g_eax;
    g_regs = saved;
    current_va = saved_va;
    pending_ordinal = saved_ordinal;
    interrupt_enabled = saved_if;
    return result;
}

static void call_dpc(uint32_t dpc, uint32_t arg1, uint32_t arg2)
{
    uint32_t args[] = {dpc, read32(dpc + 16), arg1, arg2};
    run_callback(read32(dpc + 12), 2, args, 4);
}

static void fire_timer(uint32_t address, uint32_t dpc, int periodic)
{
    write32(address + 4, 1);
    MEM8(address + 3) = periodic != 0;
    note("[TIMER] fire object=%08x dpc=%08x", address, dpc);
    if (dpc) call_dpc(dpc, 0, 0);
}

static void deliver_irq(uint32_t object, uint32_t pending, uint8_t level)
{
    if (!pending) return;
    uint8_t irql = (uint8_t)read32(object + 12);
    if (level >= irql) return;
    uint32_t args[] = {object, read32(object + 4)};
    uint32_t routine = read32(object);
    uint32_t handled = run_callback(routine, irql, args, 2);
    note("[IRQ] returned routine=%08x pending=%02x handled=%u", routine, pending, handled & 0xff);
}

static void poll_callbacks(void)
{
    uint8_t level = MEM8(g_fs_base + 0x24);
    delivering_callback = 1;
    if (usb_interrupt) deliver_irq(usb_interrupt, ngb_ohci_irq_pending(), level);
    if (apu_interrupt) deliver_irq(apu_interrupt, ngb_audio_irq(5), level);
    if (ac97_interrupt) deliver_irq(ac97_interrupt, ngb_audio_irq(6), level);
    if (gpu_interrupt) deliver_irq(gpu_interrupt, ngb_nv2a_irq_pending(), level);
    if (ngb_pending_dpcs && level < 2) {
        uint32_t object = dpc_queue[0];
        memmove(dpc_queue, dpc_queue + 1, --ngb_pending_dpcs * sizeof(*dpc_queue));
        MEM8(object + 2) = 0;
        note("[DPC] dispatch object=%08x routine=%08x", object, read32(object + 12));
        call_dpc(object, read32(object + 20), read32(object + 24));
        note("[DPC] returned object=%08x", object);
    }
    delivering_callback = 0;
}

#include "workers.inc"

#if defined(__SWITCH__) && defined(NGB_DIRECT3D)
void ngb_profile_work_counts(uint64_t *entry_count, uint64_t *poll_count, uint64_t *switches, uint64_t *skips)
{
    *entry_count = entries;
    *poll_count = ngb_guest_polls;
    *switches = fiber_switches;
    *skips = skipped_event_waits;
}

unsigned ngb_profile_worker_id(void) { return running_worker + 1; }

uintptr_t ngb_profile_fiber_stack_end(uintptr_t sp)
{
    for (size_t i = 0; i < sizeof(fibers)/sizeof(fibers[0]); ++i) {
        uintptr_t base = (uintptr_t)fibers[i].stack;
        if (base && sp >= base && sp - base < WORKER_HOST_STACK) return base + WORKER_HOST_STACK;
    }
    for (unsigned i = 0; i < WORKER_LIMIT; ++i) {
        uintptr_t base = (uintptr_t)workers[i].stack;
        if (base && sp >= base && sp - base < WORKER_HOST_STACK) return base + WORKER_HOST_STACK;
    }
    return 0;
}
#endif

static void critical_section(uint32_t ordinal)
{
    uint32_t address = arg(0);
    (void)ngb_guest_pointer(address, 28);
    unsigned i;
    for (i = 0; i < 64 && locks[i].address && locks[i].address != address; ++i) {}
    if (i == 64) ngb_stop("bootstrap lock table exhausted", address);
    locks[i].address = address;
    if (ordinal == 277) {
        while (locks[i].depth && locks[i].owner != workers[running_worker].id) {
            poll_runtime(true);
            yield_worker();
        }
        locks[i].owner = workers[running_worker].id;
        ++locks[i].depth;
    }
    else if (ordinal == 294) {
        if (!locks[i].depth || locks[i].owner != workers[running_worker].id) ngb_stop("unbalanced critical section leave", address);
        --locks[i].depth;
    } else if (locks[i].depth) ngb_stop("initializing an owned critical section", address);
    g_eax = 0;
    g_esp += 8; /* stdcall: return address and one argument */
}

static void kernel_call(void)
{
    uint32_t ordinal = pending_ordinal;
    /* Keep frequent allocator locks and page lookups from hiding later events. */
    if (ordinal >= 512 || syscall_seen[ordinal]++ < 12)
        note("[KERNEL] %u %s caller=%08x", ordinal, ngb_kernel_name(ordinal), read32(g_esp));
    if (ordinal==169 || ordinal==170) { kernel_stack(ordinal); return; }
    if (ordinal==238) { yield_worker(); g_eax=0; g_esp+=4; return; }
    if (ordinal==99) {
        int64_t delay;
        memcpy(&delay,(void *)ngb_guest_pointer(arg(2),8),8);
        if (arg(1) || delay>0 || delivering_callback || MEM8(g_fs_base+0x24)>=2)
            ngb_stop("unsupported thread delay",arg(2));
        uint64_t duration=delay ? (uint64_t)(-(delay+1))+1 : 0;
        uint64_t end=now_ns()/100+duration;
        workers[running_worker].wake_tick=end;
        do {
            yield_worker();
            if (now_ns()/100>=end) break;
            idle_if_all_waiting();
            poll_runtime(true);
            if (startup_expired()) ngb_stop("thread delay budget",current_va);
        } while (1);
        workers[running_worker].wake_tick=0;
        g_eax=0; g_esp+=16;
        return;
    }
    if (thread_object_call(ordinal) || event_call(ordinal)) return;
    if (ordinal == 255 && thread_count) { create_worker(); return; }
    if (ordinal == 258 && running_worker) {
        write32(workers[running_worker].object+0x120,arg(0));
        write32(workers[running_worker].object+4,1);
        workers[running_worker].exited = 1;
        yield_worker();
        ngb_stop("no runnable guest thread",running_worker);
    }
    if ((ordinal == 224 || ordinal == 231 || ordinal == 187) && (arg(0)>>24)==0x51) {
        struct worker *w=worker_handle(arg(0));
        if (!w) {
            g_eax=0xc0000008u;
            g_esp+=ordinal!=187 ? 12 : 8;
            return;
        }
        g_eax=w->open ? 0 : 0xc0000008u;
        if (w->open && ordinal!=187) {
            if (arg(1)) write32(arg(1),w->suspended);
            if (ordinal==231) {
                if (w->suspended==127) g_eax=0xc000004au;
                else ++w->suspended;
            } else if (w->suspended) --w->suspended;
        } else if (ordinal==187) w->open=0;
        g_esp+=ordinal!=187 ? 12 : 8;
        if (w==&workers[running_worker] && w->suspended) yield_worker();
        return;
    }
    if (ordinal == 15 || ordinal == 14) {
        uint32_t size=arg(0), rounded=size ? size : 1, address=0;
        if (!ngb_vm_allocate(&address,&rounded,0,0x3000,4)) {
            pool_sizes[(address-NGB_VM_BEGIN)/4096]=size ? size : 1;
        }
        g_eax=address;
        g_esp+=ordinal==15 ? 12 : 8;
        return;
    }
    if (ordinal == 17 || ordinal == 23) {
        uint32_t address=arg(0);
        if (address<NGB_VM_BEGIN || address>=NGB_VM_END || (address&4095))
            ngb_stop("invalid pool block",address);
        uint32_t *size=&pool_sizes[(address-NGB_VM_BEGIN)/4096];
        if (!*size) ngb_stop("unallocated pool block",address);
        if (ordinal==23) g_eax=*size;
        else {
            uint32_t release=0;
            if (ngb_vm_free(&address,&release,0x8000)) ngb_stop("pool release failed",address);
            *size=0;
        }
        g_esp+=8;
        return;
    }
    if (ordinal == 1) { /* AvGetSavedDataAddress */
        g_eax = saved_av_data;
        g_esp += 4;
        return;
    }
    if (ordinal == 4) { /* AvSetSavedDataAddress */
        saved_av_data = arg(0);
        g_esp += 8;
        return;
    }
    if (ordinal == 2) {
        uint32_t option = arg(1);
        uint32_t value = 0;
        if (option == 6) {
            value = ngb_av_pack();
            note("[AV] query AV pack=%08x", value);
        } else if (option == 0xb) {
            flicker_filter = arg(2);
            note("[AV] flicker filter=%u", flicker_filter);
        } else if (option == 0xe && !arg(3)) {
            luma_filter = arg(2) != 0;
            note("[AV] luma filter=%u", luma_filter);
        } else if (option == 9 && !arg(3) && arg(2)<=1) {
            ngb_scanout_blank(arg(2));
            note("[AV] screen blank=%u", arg(2));
        } else if (option == 0xf && arg(3) && arg(0) == 0xfd000000u) {
            value = ngb_nv2a_field();
            note("[AV] encoder field=%u", value);
        } else ngb_stop("unsupported TV encoder option", option);
        if (arg(3)) write32(arg(3), value);
        g_eax = 0; g_esp += 20;
        return;
    }
    if (ordinal == 159) {
        uint32_t event = arg(0);
        (void)ngb_guest_pointer(event, 16);
        uint64_t deadline=UINT64_MAX;
        if (arg(4)) {
            int64_t timeout;
            memcpy(&timeout,(const void *)ngb_guest_pointer(arg(4),8),8);
            if (timeout>0) ngb_stop("absolute dispatcher timeout",arg(4));
            uint64_t ticks=(uint64_t)(-(timeout+1))+1, now=now_ns()/100;
            if (ticks<=UINT64_MAX-now) deadline=now+ticks;
        }
        if (MEM8(event)>1 || MEM8(event+2)!=4 || arg(3) ||
            read32(event+8)!=event+8 || read32(event+12)!=event+8 || delivering_callback ||
            !interrupt_enabled || MEM8(g_fs_base+0x24)>=2)
            ngb_stop("unsupported dispatcher wait",event);
        while (!read32(event+4)) {
            if (now_ns()/100>=deadline) { g_eax=0x102; g_esp+=24; return; }
            workers[running_worker].wait_key = event;
            workers[running_worker].wait_until = deadline;
            workers[running_worker].wait_named = 0;
            workers[running_worker].waiting = 1;
            yield_worker();
            poll_runtime(true);
            if (!read32(event + 4)) idle_if_all_waiting();
            workers[running_worker].waiting = 0;
            if (startup_expired()) ngb_stop("dispatcher wait budget",event);
            if (atomic_load(&cancel)) { stopped_status=NGB_BOOT_CANCELLED; ngb_stop("cancel requested",event); }
        }
        if (MEM8(event)==1) write32(event+4,0);
        g_eax=0; g_esp+=24; return;
    }
    if (ordinal == 3) {
        note("[AV] display step=%u mode=%08x fmt=%08x pitch=%u fb=%08x",arg(1),arg(2),arg(3),arg(4),arg(5));
        if (arg(0)!=0xfd000000u || arg(1)!=0) ngb_stop("unsupported display mode step",arg(1));
        ngb_scanout_mode(arg(2),arg(3),arg(4),arg(5));
        ngb_nv2a_write32(0xfd600800u,arg(5));
        g_eax=0; g_esp+=28; return;
    }
    if (ordinal == 145) { /* KeSetEvent: guest-initialized dispatcher event. */
        uint32_t event = arg(0);
        (void)ngb_guest_pointer(event, 16);
        if (MEM8(event) > 1 || MEM8(event + 2) != 4 ||
            read32(event + 8) != event + 8 || read32(event + 12) != event + 8 || arg(2))
            ngb_stop("unsupported dispatcher event or waiter", event);
        g_eax = read32(event + 4);
        write32(event + 4, 1);
        g_esp += 16;
        return;
    }
    if (ordinal == 46) {
        uint32_t bus = arg(0), slot = arg(1), reg = arg(2), buf = arg(3), len = arg(4);
        /* Bus 1, slot 0 is the NV2A. The PBUS mirror and the HAL must see the
         * same AGP command word when the XDK sets the request queue depth. */
        if (bus != 1 || slot || reg != 0x4c || len != 4)
            ngb_stop("unsupported PCI configuration access", reg);
        if (arg(5)) ngb_nv2a_write32(0xfd00184c, read32(buf));
        else write32(buf, ngb_nv2a_read32(0xfd00184c));
        g_esp += 28;
        return;
    }
    if (ordinal == 44) {
        /* Xbox external interrupt vectors start at 0x30. The guest IRQL
         * decreases as the hardware IRQ number increases. */
        uint32_t irq = arg(0), irql_out = arg(1);
        g_eax = 0;
        if (irq <= 27) {
            uint8_t level = (uint8_t)(27 - irq);
            g_eax = 0x30 + irq;
            if (irql_out) MEM8(irql_out) = level;
            note("[IRQ] bus=%u vector=%02x irql=%u", irq, g_eax, level);
        }
        g_esp += 12;
        return;
    }
    if (ordinal == 103 || ordinal == 129 || ordinal == 160 || ordinal == 161) {
        uint8_t level = MEM8(g_fs_base + 0x24);
        if (ordinal != 103) {
            uint8_t next = ordinal == 129 ? 2 : (uint8_t)g_ecx;
            if (next > 31 || (ordinal == 161 ? next > level : next < level))
                ngb_stop("invalid IRQL transition", next);
            MEM8(g_fs_base + 0x24) = next;
        }
        g_eax = ordinal == 161 ? 0 : level;
        g_esp += 4;
        return;
    }
    if (ordinal == 98 || ordinal == 100) {
        uint32_t object = arg(0);
        (void)ngb_guest_pointer(object, 0x70);
        uint32_t line = read32(object + 8);
        if (line != 1 && line != 3 && line != 5 && line != 6) ngb_stop("unsupported interrupt line", line);
        uint32_t *slot = line == 1 ? &usb_interrupt : line == 3 ? &gpu_interrupt :
                         line == 5 ? &apu_interrupt : &ac97_interrupt;
        g_eax = 0;
        if (ordinal == 98 && !*slot && !MEM8(object + 16) &&
            read32(object + 12) == 27u - line && recomp_lookup(read32(object))) {
            *slot = object;
            MEM8(object + 16) = 1;
            g_eax = 1;
            note("[IRQ] connected bus=%u object=%08x", line, object);
        } else if (ordinal == 100 && *slot == object && object) {
            *slot = 0;
            MEM8(object + 16) = 0;
            g_eax = 1;
        }
        g_esp += 8;
        return;
    }
    if (ordinal == 119) {
        uint32_t object = arg(0);
        (void)ngb_guest_pointer(object, 28);
        if (MEM16(object) != 0x13) ngb_stop("invalid queued DPC", object);
        g_eax = 0;
        if (!MEM8(object + 2)) {
            if (ngb_pending_dpcs == sizeof(dpc_queue) / sizeof(*dpc_queue)) ngb_stop("DPC queue full", object);
            write32(object + 20, arg(1)); write32(object + 24, arg(2));
            MEM8(object + 2) = 1; dpc_queue[ngb_pending_dpcs++] = object;
            note("[DPC] queued object=%08x", object);
            g_eax = 1;
        }
        g_esp += 16;
        return;
    }
    if (ordinal == 109) {
        uint32_t object = arg(0), routine = arg(1), context = arg(2), vector = arg(3);
        uint32_t irql = (uint8_t)arg(4), mode = arg(5), share = (uint8_t)arg(6);
        if (vector < 0x30 || vector > 0x30 + 27 || irql > 31 || mode > 1)
            ngb_stop("invalid interrupt parameters", vector);
        /* Xbox KINTERRUPT is 0x70 bytes. Keep guest addresses in its
         * header. Connecting and delivering the ISR are separate services. */
        memset((void *)ngb_guest_pointer(object, 0x70), 0, 0x70);
        write32(object, routine);
        write32(object + 4, context);
        write32(object + 8, vector - 0x30);
        write32(object + 12, irql);
        MEM8(object + 17) = share != 0;
        MEM8(object + 18) = (uint8_t)mode;
        note("[IRQ] initialized object=%08x vector=%02x routine=%08x context=%08x",
             object, vector, routine, context);
        g_esp += 32;
        return;
    }
    if (ordinal == 153) { /* KeSynchronizeExecution */
        uint32_t object=arg(0), routine=arg(1), context=arg(2);
        (void)ngb_guest_pointer(object, 0x70);
        uint32_t level=read32(object+12);
        uint8_t previous=MEM8(g_fs_base+0x24);
        recomp_func_t fn=recomp_lookup(routine);
        if (!fn || level<previous || level>31)
            ngb_stop("invalid synchronized interrupt callback",routine);
        /* May already be on the DPC stack. Run the stdcall on this stack
         * at the interrupt's IRQL so its driver state cannot be reentered. */
        uint32_t stack=g_esp, caller=current_va;
        int outer_callback=delivering_callback;
        delivering_callback=1;
        MEM8(g_fs_base+0x24)=(uint8_t)level;
        PUSH32(g_esp,context);
        PUSH32(g_esp,0);
        fn();
        if (g_esp!=stack) ngb_stop("unbalanced synchronized callback",routine);
        pending_ordinal=ordinal;
        current_va=caller;
        MEM8(g_fs_base+0x24)=previous;
        delivering_callback=outer_callback;
        g_eax &= 255u;
        g_esp+=16;
        return;
    }
    if (ordinal == 151) {
        uint32_t us = arg(0);
        uint64_t until = now_ns() + (uint64_t)us * 1000;
        while (now_ns() < until) {
            if (atomic_load(&cancel)) {
                stopped_status = NGB_BOOT_CANCELLED;
                ngb_stop("cancel requested", current_va);
            }
            if (startup_expired()) ngb_stop("bootstrap time budget reached", current_va);
        }
        g_esp += 8;
        return;
    }
    if (ordinal == 128) {
        uint32_t dest = arg(0);
        (void)ngb_guest_pointer(dest, 8);
        struct timespec ts;
        if (clock_gettime(CLOCK_REALTIME, &ts)) ngb_stop("system clock unavailable", ordinal);
        uint64_t ticks = 116444736000000000ull + (uint64_t)ts.tv_sec * 10000000 + ts.tv_nsec / 100;
        write32(dest, (uint32_t)ticks); write32(dest + 4, (uint32_t)(ticks >> 32));
        g_eax = 0; g_esp += 8;
        return;
    }
    if (ordinal == 327 || ordinal == 328) {
        /* All XBE sections were loaded from the validated image. Match the
         * upstream reference-count behaviour; do not reread or unmap them. */
        uint32_t section = arg(0), table = read32(0x10120), count = read32(0x1011c);
        if (section < table || (section - table) % 56 || (section - table) / 56 >= count) {
            g_eax = 0xc000000d;
        } else {
            uint32_t refs = read32(section + 24);
            if ((ordinal == 327 && refs == UINT32_MAX) || (ordinal == 328 && !refs)) g_eax = 0xc000000d;
            else {
                refs = ordinal == 327 ? refs + 1 : refs - 1;
                write32(section + 24, refs); g_eax = 0;
                note("[SECTION] %s index=%u refs=%u", ordinal == 327 ? "load" : "unload", (section - table) / 56, refs);
            }
        }
        g_esp += 8;
        return;
    }
    if (ordinal == 279) {
        g_eax = ngb_equal_string(arg(0), arg(1), arg(2)); g_esp += 16;
        return;
    }
    if (ordinal == 289) {
        /* RtlInitAnsiString uses an 8-byte guest descriptor, not the host's
         * native structure with its 64-bit Buffer pointer. */
        uint32_t dest = arg(0), source = arg(1), length = 0;
        (void)ngb_guest_pointer(dest, 8);
        if (source) while (length < 0xfffe && MEM8(source + length)) ++length;
        write32(dest, source ? length | (length + 1) << 16 : 0);
        write32(dest + 4, source);
        g_eax = 0; g_esp += 12;
        return;
    }
    if (ordinal==340) {
        uint32_t a[7];
        for (unsigned i=0;i<7;++i) a[i]=arg(i);
        ngb_xc_hmac(a); g_eax=0; g_esp+=32;
        return;
    }
    if (ordinal>=335 && ordinal<=337) {
        uint32_t data=ordinal==335 ? 0 : arg(1);
        ngb_xc_sha(ordinal,arg(0),data,ordinal==336 ? arg(2) : 0);
        g_eax=0;
        g_esp+=ordinal==335 ? 8 : ordinal==336 ? 16 : 12;
        return;
    }
    unsigned file_args = ngb_files_arg_count(ordinal);
    if (file_args) {
        uint32_t args[10];
        for (unsigned i = 0; i < file_args; ++i) args[i] = arg(i);
        g_eax = ngb_files_dispatch(ordinal, args);
        g_esp += 4 + file_args * 4;
        return;
    }
    if (ordinal == 149 || ordinal == 150) {
        uint32_t object = arg(0), dpc = arg(ordinal == 149 ? 3 : 4);
        int64_t due = (int64_t)((uint64_t)arg(1) | (uint64_t)arg(2) << 32);
        int32_t period = ordinal == 149 ? 0 : (int32_t)arg(3);
        if (period < 0) ngb_stop("negative timer period", (uint32_t)period);
        uint64_t delay;
        if (due < 0) delay = (uint64_t)(-(due + 1)) + 1;
        else {
            struct timespec ts;
            clock_gettime(CLOCK_REALTIME, &ts);
            uint64_t wall = 116444736000000000ull + (uint64_t)ts.tv_sec * 10000000 + ts.tv_nsec / 100;
            delay = (uint64_t)due > wall ? (uint64_t)due - wall : 0;
        }
        int was_set = ngb_timer_arm(object, now_ns() / 100, delay, (uint64_t)period * 10000, dpc);
        if (was_set < 0) ngb_stop("timer not initialized", object);
        write32(object + 4, 0);
        MEM8(object + 3) = 1;
        write32(object + 16, (uint32_t)due);
        write32(object + 20, (uint32_t)((uint64_t)due >> 32));
        write32(object + 32, dpc); write32(object + 36, (uint32_t)period);
        note("[TIMER] armed object=%08x delay_100ns=%llu period_ms=%d", object,
             (unsigned long long)delay, period);
        g_eax = (uint32_t)was_set; g_esp += ordinal == 149 ? 20 : 24;
        return;
    }
    if (ordinal == 97) {
        uint32_t object = arg(0);
        int was_set = ngb_timer_cancel(object);
        if (was_set < 0) ngb_stop("timer not initialized", object);
        MEM8(object + 3) = 0;
        g_eax = (uint32_t)was_set; g_esp += 8;
        return;
    }
    if (ordinal == 301) {
        g_eax = ngb_status_to_error(arg(0)); g_esp += 8;
        return;
    }
    if (ordinal == 184 || ordinal == 199) {
        uint32_t bp = arg(0), sp = arg(ordinal == 184 ? 2 : 1);
        uint32_t base = read32(bp), size = read32(sp);
        uint32_t flags = arg(ordinal == 184 ? 3 : 2);
        uint32_t status = ordinal == 184 ?
            ngb_vm_allocate(&base, &size, arg(1), flags, arg(4)) :
            ngb_vm_free(&base, &size, flags);
        if (!status) { write32(bp, base); write32(sp, size); }
        note("[VM] %s base=%08x bytes=%u flags=%x status=%08x",
             ordinal == 184 ? "allocate" : "free", base, size, flags, status);
        g_eax = status; g_esp += ordinal == 184 ? 24 : 16;
        return;
    }
    if (ordinal == 217) {
        uint32_t address = arg(0), info[7] = {0}, allocation_size;
        if (address >= NGB_VM_BEGIN && address < NGB_VM_END) {
            g_eax = ngb_vm_query(address, info);
        } else if (ngb_contiguous_query(address, info, &allocation_size)) {
            g_eax = 0;
        } else if (address >= 0x1000 && address < RAM_BYTES) {
            info[0] = info[1] = address & ~0xfffu;
            info[2] = info[5] = 4;
            info[3] = (address < NGB_VM_BEGIN ? NGB_VM_BEGIN : RAM_BYTES) - info[0];
            info[4] = 0x1000; info[6] = 0x20000;
            g_eax = 0;
        } else {
            info[0] = address & ~0xfffu; info[3] = 4096; info[4] = 0x10000;
            g_eax = 0;
        }
        memcpy((void *)ngb_guest_pointer(arg(1), sizeof(info)), info, sizeof(info));
        g_esp += 12;
        return;
    }
    if (ordinal == 24) {
        g_eax = ngb_query_setting(arg(0), arg(1), arg(2), arg(3), arg(4));
        g_esp += 24;
        return;
    }
    if (ordinal == 47) {
        /* Match upstream's process-exit model: these callbacks belong to an
         * Xbox shutdown, not exiting this application to hbmenu. Retain the
         * registrations; an Xbox shutdown request remains unsupported. */
        uint32_t address = arg(0), enable = arg(1);
        (void)ngb_guest_pointer(address, 16);
        unsigned i;
        for (i = 0; i < 32 && shutdown_registrations[i] != address; ++i) {}
        if (!enable) { if (i < 32) shutdown_registrations[i] = 0; }
        else if (i == 32) {
            for (i = 0; i < 32 && shutdown_registrations[i]; ++i) {}
            if (i == 32) ngb_stop("shutdown registration table full", address);
            shutdown_registrations[i] = address;
        }
        note("[SHUTDOWN] %s registration=%08x (Xbox shutdown only)", enable ? "register" : "unregister", address);
        g_eax = 0; g_esp += 12;
        return;
    }
    if (ordinal == 277 || ordinal == 291 || ordinal == 294) {
        critical_section(ordinal);
        return;
    }
    if (ordinal == 107) {
        /* Guest KDPC carries a callback, context and two deferred arguments. */
        uint32_t object = arg(0), routine = arg(1), context = arg(2);
        memset((void *)ngb_guest_pointer(object, 28), 0, 28);
        write32(object, 0x13);
        write32(object + 12, routine);
        write32(object + 16, context);
        g_eax = 0; g_esp += 16;
        return;
    }
    if (ordinal == 113) {
        uint32_t object = arg(0), type = arg(1);
        if (type > 1) ngb_stop("invalid timer type", type);
        memset((void *)ngb_guest_pointer(object, 40), 0, 40);
        write32(object, 0x00280008u + type);
        if (ngb_timer_initialize(object) < 0) ngb_stop("timer table exhausted", object);
        g_eax = 0; g_esp += 12;
        return;
    }
    /* The XBE entry creates its first thread to run XAPI startup. This
     * bootstrap performs only that initial handoff, as upstream's INLINE
     * mode does. A second guest thread requires the real scheduler. */
    if (ordinal == 255 && thread_count == 0 && arg(7) == 0) {
        uint32_t routine = arg(9), ctx1 = arg(5), ctx2 = arg(6);
        recomp_func_t fn = recomp_lookup(routine);
        if (!fn) ngb_stop("missing initial thread routine", routine);
        workers[0].id=1;
        workers[0].object=read32(g_fs_base+0x28);
        ++thread_count;
        note("[THREAD] initial handoff routine=%08x context=%08x/%08x", routine, ctx1, ctx2);
        uint32_t saved_sp = g_esp;
        g_esp = BOOT_STACK_TOP - 0x10000;
        PUSH32(g_esp, ctx2); PUSH32(g_esp, ctx1); PUSH32(g_esp, 0);
        fn();
        g_esp = saved_sp;
        ngb_stop("initial thread returned; scheduler not yet connected", routine);
    }
    if (ordinal == 165 || ordinal == 166) {
        uint32_t bytes = arg(0), low = 0, high = UINT32_MAX, alignment = 0, protect = 4;
        if (ordinal == 166) {
            low = arg(1); high = arg(2); alignment = arg(3); protect = arg(4);
        }
        if (protect != 4 && protect != 0x404) ngb_stop("unsupported contiguous memory protection", protect);
        g_eax = ngb_contiguous_allocate(bytes, low, high, alignment, protect);
        note("[MEMORY] contiguous bytes=%u low=%08x high=%08x alignment=%u protect=%08x va=%08x",
             bytes, low, high, alignment, protect, g_eax);
        /* Verify both ends through the CPU mapping before the title owns the
         * pages. Restore the zeroes the caller expects from a new allocation. */
        if (g_eax && bytes >= 2) {
            volatile uint8_t *first = ngb_contiguous_pointer(g_eax, bytes);
            if (!first) ngb_stop("missing contiguous mapping", g_eax);
            volatile uint8_t *last = first + bytes - 1;
            if (*first || *last) ngb_stop("contiguous pages were not cleared", g_eax);
            *first = 0x5a; *last = 0xa5;
            volatile uint8_t *mapped_last = ngb_contiguous_pointer(g_eax + bytes - 1, 1);
            if (!mapped_last || *first != 0x5a || *mapped_last != 0xa5)
                ngb_stop("contiguous readback failed", g_eax);
            *first = 0; *last = 0;
            note("[MEMORY] readback passed va=%08x bytes=%u", g_eax, bytes);
        }
        g_esp += ordinal == 165 ? 8 : 24;
        return;
    }
    if (ordinal == 168) {
        uint32_t bytes = arg(0), padding_out = arg(1);
        if (padding_out) (void)ngb_guest_pointer(padding_out, 4);
        g_eax = ngb_instance_claim(bytes);
        if (padding_out) write32(padding_out, g_eax ? NGB_INSTANCE_PADDING : 0);
        note("[MEMORY] GPU instance claim bytes=%u padding_out=%08x top=%08x padding=%08x",
             bytes, padding_out, g_eax, g_eax ? NGB_INSTANCE_PADDING : 0);
        g_esp += 12;
        return;
    }
    if (ordinal == 171) {
        uint32_t va = arg(0);
        if (!ngb_contiguous_free(va)) ngb_stop("invalid contiguous free", va);
        g_eax = 0; g_esp += 8;
        return;
    }
    if (ordinal == 175) {
        uint32_t va = arg(0), bytes = arg(1);
        int unlock = (uint8_t)arg(2) != 0;
        if (va>=0x80000000u && va<0x80001000u && bytes && bytes<=0x80001000u-va) {
            if (unlock ? !page_zero_pins : page_zero_pins==UINT16_MAX)
                ngb_stop("unbalanced physical page zero lock",va);
            page_zero_pins+=unlock ? -1 : 1;
        } else if (!pin_image(va,bytes,unlock) && !ngb_vm_pin(va,bytes,unlock) && !ngb_contiguous_pin(va, bytes, unlock)) ngb_stop("invalid contiguous page lock", va);
        note("[MEMORY] %s pages va=%08x bytes=%u", unlock ? "unlock" : "lock", va, bytes);
        g_eax = 0; g_esp += 16;
        return;
    }
    if (ordinal == 182) {
        note("[MEMORY] protect va=%08x bytes=%u protect=%08x",arg(0),arg(1),arg(2));
        if (!ngb_contiguous_protect(arg(0),arg(1),arg(2))) ngb_stop("unsupported page protection change",arg(0));
        g_esp+=16;
        return;
    }
    if (ordinal == 180 || ordinal == 179) {
        uint32_t address=arg(0), info[7], bytes;
        if (!ngb_contiguous_query(address,info,&bytes))
            ngb_stop("unmapped memory query",address);
        g_eax = ordinal==180 ? bytes : info[5];
        g_esp+=8;
        return;
    }
    if (ordinal == 173) {
        g_eax = ngb_contiguous_physical(arg(0)); g_esp += 8;
        return;
    }
    ngb_stop(ngb_kernel_name(ordinal), ordinal);
}

recomp_func_t recomp_lookup_kernel(uint32_t va)
{
    if (va < THUNK_BASE || ((va - THUNK_BASE) & 3u)) return NULL;
    uint32_t slot = (va - THUNK_BASE) / 4;
    if (slot >= thunk_count) return NULL;
    pending_ordinal = thunk_ordinals[slot];
    return kernel_call;
}
recomp_func_t recomp_lookup_manual(uint32_t va) { (void)va; return NULL; }
void recomp_icall_fail_log(uint32_t va) { ngb_stop("unresolved indirect call", va); }
void recomp_icall_not_code_log(uint32_t va) { ngb_stop("invalid indirect call", va); }
void recomp_unimpl(const char *text, uint32_t va)
{
    if (!strcmp(text, "cli")) { interrupt_enabled = false; return; }
    if (!strcmp(text, "sti")) { interrupt_enabled = true; return; }
    /* The boot DMA reader and guest share ordinary CPU memory. Order the
     * guest's command stores before it publishes PUT. */
    if (!strcmp(text, "wbinvd")) { atomic_thread_fence(memory_order_seq_cst); return; }
    note("[INSTRUCTION] %s", text);
    ngb_stop("unimplemented instruction", va);
}
void recomp_debug_service(uint32_t service, uint32_t va) { note("[DEBUG] service=%u arg=%08x", service, va); }
uint64_t xbox_ReadTimeStampCounter(void) { uint64_t n = now_ns() - start_ns; return n / 1000000000u * 733333333u + n % 1000000000u * 733333333u / 1000000000u; }
static uint8_t encoder_gpio;
uint32_t xbox_PortIn(uint32_t port, int size)
{
    if (port == 0x80c0 && size == 1)
        return (encoder_gpio & ~0x20u) | ((ngb_elapsed_ns() / 16666667u & 1u) << 5);
    ngb_stop("port read", port);
}
void xbox_PortOut(uint32_t port, uint32_t value, int size)
{
    if (port != 0x80c0 || size != 1) ngb_stop("port write", port);
    encoder_gpio = (uint8_t)value;
    note("[PORT] encoder GPIO=%02x", encoder_gpio);
}
void recomp_spin_pause(uint32_t va) { ngb_checkpoint(va); }
int recomp_capture_entry(uint32_t va) { ngb_checkpoint(va); return 0; }
void recomp_trace_enter(const char *name, uint32_t va) { (void)name; ngb_checkpoint(va); }
void recomp_trace_exit(const char *name, uint32_t va) { (void)name; (void)va; }
void recomp_trace_esp(const char *name, const char *tag) { note("[ESP] %s %s %08x", name, tag, g_esp); }
jmp_buf *recomp_setjmp_slot(uint32_t va) { ngb_stop("guest setjmp not connected", va); }
int recomp_guest_longjmp(uint32_t va, uint32_t value) { (void)value; ngb_stop("guest longjmp not connected", va); }

static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static int load_image(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) { note("[ERROR] cannot open %s", path); return 0; }
    unsigned char *xbe = malloc(NGB_IMAGE_BYTES);
    size_t got = xbe ? fread(xbe, 1, NGB_IMAGE_BYTES, f) : 0;
    int extra = fgetc(f);
    fclose(f);
    uint64_t hash = 0xcbf29ce484222325ull;
    for (size_t i = 0; i < got; ++i) hash = (hash ^ xbe[i]) * 0x100000001b3ull;
    if (got != NGB_IMAGE_BYTES || extra != EOF || hash != NGB_IMAGE_FNV) {
        note("[ERROR] image mismatch: bytes=%zu FNV=%016llx", got, (unsigned long long)hash);
        free(xbe); return 0;
    }
    uint32_t base = le32(xbe + 0x104), headers = le32(xbe + 0x108);
    uint32_t count = le32(xbe + 0x11c), table = le32(xbe + 0x120) - base;
    uint32_t entry = le32(xbe + 0x128) ^ 0xa8fc57abu;
    if (memcmp(xbe, "XBEH", 4) || base != 0x10000 || headers > got ||
        (uint64_t)table + (uint64_t)count * 56 > got || entry != 0x0032b385) {
        free(xbe); return 0;
    }
    /* The desktop lift leaves the low guest page backed by zeroed RAM unless
     * RECOMP_TRAP_NULL is selected. The guest D3D resource lookup reads it. */
    trap_null = getenv("RECOMP_TRAP_NULL") != NULL;
    ram = calloc(1, 2u * RAM_BYTES);
    if (!ram) { free(xbe); return 0; }
    ngb_contiguous_set_ram(ram);
    ngb_scene_memory(ram, 2u * RAM_BYTES);
    g_xbox_mem_offset = (ptrdiff_t)(uintptr_t)ram;
    memset(image_resident,0,sizeof(image_resident));
    memset(image_pins,0,sizeof(image_pins));
    memcpy(ram + base, xbe, headers);
    for (uint32_t i = 0; i < count; ++i) {
        const unsigned char *s = xbe + table + i * 56;
        uint32_t va = le32(s+4), vs = le32(s+8), raw = le32(s+12), rs = le32(s+16);
        if ((uint64_t)va + vs > RAM_BYTES || rs > vs || (uint64_t)raw + rs > got) {
            note("[ERROR] invalid section %u", i); free(xbe); return 0;
        }
        if (vs) memset(image_resident+va/4096,1,(va+vs-1)/4096-va/4096+1);
        memcpy(ram + va, xbe + raw, rs);
        if (le32(s) & 4) {
            if (!g_xbox_code_lo || va < g_xbox_code_lo) g_xbox_code_lo = va;
            if (va + vs > g_xbox_code_hi) g_xbox_code_hi = va + vs;
        }
        note("[SECTION] %u va=%08x bytes=%u bss=%u", i, va, rs, vs-rs);
    }
    uint32_t thunks = le32(xbe + 0x158) ^ 0x5b6d40b6u;
    free(xbe);
    for (thunk_count = 0; thunk_count < 512; ++thunk_count) {
        uint32_t ordinal = read32(thunks + thunk_count * 4);
        if (!ordinal) break;
        if (!(ordinal & 0x80000000u)) return 0;
        thunk_ordinals[thunk_count] = ordinal & 0x7fffffffu;
        uint32_t target = THUNK_BASE + thunk_count * 4;
        /* Same retail hardware/version model as upstream kernel_bridge.c.
         * These exports are data, not executable service thunks. */
        if ((ordinal & 0x7fffffff) == 322) target = 0x7000;
        if ((ordinal & 0x7fffffff) == 324) target = 0x7010;
        if ((ordinal & 0x7fffffff) == 164) target = 0x7030;
        if ((ordinal & 0x7fffffff) == 323) target = 0x7100; /* XboxHDKey */
        if ((ordinal & 0x7fffffff) == 325) target = 0x7110; /* XboxSignatureKey */
        if ((ordinal & 0x7fffffff) == 326) target = 0x7040;
        if ((ordinal & 0x7fffffff) == 356) target = 0x7058;
        if ((ordinal & 0x7fffffff) == 156) target = GUEST_TICK_COUNT;
        if ((ordinal & 0x7fffffff) == 40) target = 0x7050;
        write32(thunks + thunk_count * 4, target);
    }
    if (thunk_count == 512) return 0;
    note("[LOADER] %u sections, %u kernel imports; code=%08x..%08x", count, thunk_count, g_xbox_code_lo, g_xbox_code_hi);
    return 1;
}

static void initialize_thread(void)
{
    /* Reuse upstream's synthetic zero-section kernel header for XAPI's x86
     * cache-init inspection. It is separate from the virtual image backing. */
    memset(kernel_page, 0, sizeof(kernel_page));
    write32(0x8001003c, 0x80);
    /* Keep bootstrap-owned structures below the image base, outside its BSS. */
    write32(g_fs_base, 0xffffffff);
    write32(g_fs_base + 8, BOOT_STACK_TOP - 0x100000);
    write32(g_fs_base + 0x18, g_fs_base);
    write32(g_fs_base + 0x20, 0x6000);
    write32(g_fs_base + 0x28, 0x5000);
    write32(0x5000 + 0x28, 0x8000);
    write32(0x7000, 0); /* retail hardware flags */
    write32(0x7004, 0x0000b1a1); /* NV2A/MCPX revisions */
    write32(0x7010, 1); /* kernel major=1, minor=0 */
    write32(0x7014, 5849); /* build, QFE=0 */
    write32(0x7030, 0); /* cold boot, no title-to-title launch data */
    write32(0x7058, 0); /* upstream cold-boot SMC video mode */
    write32(0x7050, 3); /* X, Y and Z cache partitions, as in the virtual disk table */
    memset((void *)ngb_guest_pointer(0x7100,32),0,32); /* same synthetic key data as the desktop kernel */
    const char image_name[] = "\\Device\\CdRom0\\default.xbe";
    write32(0x7040, (uint32_t)(sizeof(image_name) - 1) | (uint32_t)sizeof(image_name) << 16);
    write32(0x7044, 0x7080);
    memcpy((void *)ngb_guest_pointer(0x7080, sizeof(image_name)), image_name, sizeof(image_name));
    uint32_t dir = read32(0x10000 + 0x12c);
    if (!dir) ngb_stop("missing image TLS directory", dir);
    uint32_t begin = read32(dir), end = read32(dir + 4), zero = read32(dir + 16);
    if (end < begin || (uint64_t)end - begin + zero > 0x7000)
        ngb_stop("image TLS exceeds bootstrap area", dir);
    uint32_t total = ((end - begin + zero + 15) & ~15u) + 4;
    write32(g_fs_base + 4, 0x8000 + total);
    /* XAPI's original thread trampoline copies the template and fills slot 0. */
    note("[TLS] block=00008000 size=%u fs=%08x", total, g_fs_base);
}

int ngb_boot(const char *path, FILE *log)
{
    boot_log = log;
    log_lines = 0;
    menu_cursor = UINT32_MAX;
    memset(syscall_seen,0,sizeof(syscall_seen));
    reported_contiguous_access = 0;
    page_zero_pins=0;
    memset(physical_page_zero, 0, sizeof(physical_page_zero));
    stopped_status = NGB_BOOT_UNSUPPORTED;
    snprintf(stopped_reason, sizeof(stopped_reason), "not started");
    atomic_store(&cancel, false);
    entries = 0; ngb_guest_polls = 0; ngb_poll_mask = 3; thread_count = 0; thunk_count = 0;
    g_xbox_code_lo = g_xbox_code_hi = 0;
    g_icall_count = g_icall_trace_idx = 0;
    memset(locks, 0, sizeof(locks));
    memset(pool_sizes,0,sizeof(pool_sizes));
    memset(shutdown_registrations, 0, sizeof(shutdown_registrations));
    delivering_callback = 0;
    interrupt_enabled = true;
    usb_interrupt = gpu_interrupt = apu_interrupt = ac97_interrupt = 0; ngb_pending_dpcs = 0;
    ngb_video_init();
    ngb_timers_reset();
    ngb_ohci_reset();
    ngb_audio_reset();
    ngb_nv2a_reset();
    ngb_scanout_reset();
    ngb_select_movie(0);
    flicker_filter = luma_filter = saved_av_data = 0;
    encoder_gpio = 0;
    memset(&g_regs, 0, sizeof(g_regs));
    g_fs_base = 0x4000;
    g_fp_control_word = 0x37f;
    g_fp_cc = 0x4000;
    start_ns = now_ns();
    startup_deadline = start_ns + BOOT_BUDGET_NS;
    #ifdef NGB_RIGID_CLIP
    note("[BOOT] NGB Switch startup adapter 0.51.0-rc1; ARM guest registers and rigid clip");
#elif defined(NGB_REGISTER_PACKAGE)
    note("[BOOT] NGB Switch startup adapter 0.50.0-rc1; ARM guest registers");
#else
    note("[BOOT] NGB Switch startup adapter 0.49.0; sampled render timing");
#endif
    note("[IMAGE] expected SHA256=%s", NGB_IMAGE_SHA256);
    if (!setjmp(stop_context)) {
        if (!load_image(path)) {
            stopped_status = NGB_BOOT_ERROR;
            snprintf(stopped_reason, sizeof(stopped_reason), "Unable to load default.xbe. Check that the disc matches Ninja Gaiden Black.");
        } else {
            ngb_vm_init(ram);
            initialize_thread();
            g_esp = BOOT_STACK_TOP;
            PUSH32(g_esp, 0);
            note("[BOOT] executing recompiled xbe_entry_point=0032b385; functions=%zu", recomp_get_count());
            xbe_entry_point();
            stopped_status = NGB_BOOT_RETURNED;
            snprintf(stopped_reason, sizeof(stopped_reason), "XBE entry returned");
        }
    }
    note("[RESULT] status=%d reason=%s", stopped_status, stopped_reason);
    ngb_scene_close();
    for (unsigned i=0;i<128;++i) free(fibers[i].stack);
    memset(fibers,0,sizeof(fibers));
    memset(kernel_stack_sizes,0,sizeof(kernel_stack_sizes));
    reset_workers();
    memset(events,0,sizeof(events));
    event_serial=0;
    ngb_devices_reset();
    ngb_menu_gpu_close();
    ngb_contiguous_reset();
    free(ram); ram = NULL; g_xbox_mem_offset = 0;
    ngb_vm_init(NULL);
    ngb_files_close_all();
    return stopped_status;
}
int ngb_stop_requested(void) { return atomic_load(&cancel); }
void ngb_request_stop(void) { atomic_store(&cancel, true); }
const char *ngb_boot_reason(void) { return stopped_reason; }
/* Only the cooperative guest thread owns a statistics batch. Format and
 * publish the whole report at its frame boundary, not one SD flush per line.
 * Other threads and non-statistics logs continue to use their normal path. */
static _Thread_local struct { size_t used; int active; char text[4096]; } scene_report;
static void flush_scene_report(void)
{
    if (scene_report.used && boot_log) {
        fwrite(scene_report.text,1,scene_report.used,boot_log);
        fflush(boot_log);
    }
    scene_report.used=0;
}
void ngb_scene_log_begin(void) { scene_report.active=1; }
void ngb_scene_log_end(void) { flush_scene_report(); scene_report.active=0; }
void ngb_kernel_log(const char *message) {
    if (!boot_log) return;
    if (boot_log && log_lines>=2048 && (!strncmp(message,"DirectSound stop ",17) || !strncmp(message,"Disc read unavailable ",22) || !strncmp(message,"3D scene ",9) || !strncmp(message,"Main menu ",10) || !strncmp(message,"Opening movie ",14) || !strncmp(message,"Movie content changes=",21) || !strncmp(message,"Warning fade steps=",19) || !strncmp(message,"Buffered warning Start",22) || !strncmp(message,"scanout captured",16) || !strcmp(message,"First decoded movie frame drawn") || !strcmp(message,"First Start report delivered"))) {
        if (scene_report.active && !strncmp(message,"3D scene ",9)) {
            const size_t len=strlen(message),need=10+len+1;
            if (need>sizeof(scene_report.text)-scene_report.used) flush_scene_report();
            if (need<=sizeof(scene_report.text)) {
                char *to=scene_report.text+scene_report.used;
                memcpy(to,"[SERVICE] ",10); memcpy(to+10,message,len);
                to[10+len]='\n'; scene_report.used+=need;
                return;
            }
        }
        fprintf(boot_log,"[SERVICE] %s\n",message);
        fflush(boot_log);
    } else note("[SERVICE] %s", message);
}
