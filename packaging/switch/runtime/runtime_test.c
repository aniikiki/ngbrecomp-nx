/* Exercise private bridge boundaries against the real generated code. This
 * host-only executable is never packaged for Switch. */
#include "runtime.c"
#include "pgraph_boot.h"
#include "frontend_input.h"
#include "apu/apu_regs.h"
#include <unistd.h>
#include "usb/usb_gamepad.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)

/* Let the real USB debounce timer expire at the first PRAMIN write, as it
 * did on the Switch. The wrapper is linked only into the host test. */
static int test_start_button, test_movie_frames, benchmark_scene, benchmark_motion;
static int benchmark_combat, combat_verified;
static uint32_t test_movie_address;
void __real_ngb_kernel_log(const char *);
void __wrap_ngb_kernel_log(const char *message)
{
    if (sscanf(message,"PGRAPH decoded movie frame drawn physical=%x",&test_movie_address)==1)
        ++test_movie_frames;
    __real_ngb_kernel_log(message);
    if (!strncmp(message,"3D scene flips=",15) && getenv("NGB_TEST_STORY")) {
        static uint64_t prev_cpu,prev_work;
        static unsigned prev_flip,prev_draws;
        struct timespec t; unsigned flip,draws;
        CHECK(sscanf(message,"3D scene flips=%u draws=%u",&flip,&draws)==2);
        CHECK(!clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t));
        uint64_t cpu=(uint64_t)t.tv_sec*1000000000u+t.tv_nsec;
        if (prev_flip && flip>prev_flip) fprintf(stderr,
            "[STORYCPU] frames=%u..%u guest_ms_per_frame=%.3f draws_per_frame=%.1f entries_per_frame=%.0f\n",
            prev_flip+1,flip,(cpu-prev_cpu)/1e6/(flip-prev_flip),(double)(draws-prev_draws)/(flip-prev_flip),
            (double)(entries-prev_work)/(flip-prev_flip));
        prev_cpu=cpu;prev_work=entries;prev_flip=flip;prev_draws=draws;
    }
    if (benchmark_combat && !strncmp(message, "3D scene flips=", 15)) {
        static uint64_t previous_ns, previous_entries, previous_polls;
        static unsigned previous_draws;
        unsigned flip, draws;
        CHECK(sscanf(message, "3D scene flips=%u draws=%u", &flip, &draws) == 2);
        if (flip == 30 || flip == 120 || flip == 1680 || flip == 1800 || flip == 1920) {
            struct timespec t;
            CHECK(clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t) == 0);
            uint64_t ns = (uint64_t)t.tv_sec * 1000000000u + t.tv_nsec;
            if (previous_ns && flip != 1680)
                fprintf(stderr, "[OFFLINE] end=%u draws=%u guest_ms=%.3f entries=%llu polls=%llu\n",
                        flip, draws - previous_draws, (ns - previous_ns) / 1e6,
                        (unsigned long long)(entries - previous_entries),
                        (unsigned long long)(ngb_guest_polls - previous_polls));
            previous_entries = entries;
            previous_polls = ngb_guest_polls;
            previous_ns = ns;
            previous_draws = draws;
            if (flip == 1920) {
                CHECK(benchmark_motion);
                combat_verified = 1;
                ngb_stop("verified original combat window", flip);
            }
        }
    }
    if (benchmark_scene && !strncmp(message, "3D scene flips=120 ", 19)) {
        CHECK(benchmark_motion);
        ngb_stop("verified 120 original demo frames", 120);
    }
}

/* Sample the same scaled snapshot that the Switch frontend reads. Verify
 * motion independently of the decoder's frame counter and test menu exit. */
void __real_ngb_scanout_publish_movie(void);
void __wrap_ngb_scanout_publish_movie(void)
{
    static unsigned count, changes;
    static uint32_t previous;
    uint32_t frame[72][128], hash=2166136261u;
    __real_ngb_scanout_publish_movie();
    ngb_scanout_blit(&frame[0][0],128,128,72);
    for (unsigned y=5;y<67;++y)
        for (unsigned x=23;x<105;++x) hash=(hash^frame[y][x])*16777619u;
    if (!count || hash!=previous) ++changes;
    previous=hash;
    ++count;
    if (count==600) printf("[TEST] opening display frames=%u changes=%u\n",count,changes);
    if (count==10 && getenv("NGB_TEST_CANCEL_OPENING")) ngb_request_stop();
}

/* Sample the stable logo and heading from the actual guest display surface.
 * The reference crops exclude the blinking prompt and menu highlight. */
static uint32_t frame_signature(const uint32_t *pixels, unsigned x0, unsigned x1, unsigned dx,
                                unsigned y0, unsigned y1, unsigned dy)
{
    uint32_t hash = 2166136261u;
    for (unsigned y = y0; y < y1; y += dy)
        for (unsigned x = x0; x < x1; x += dx)
            hash = (hash ^ (pixels[y*768 + x] & 0xffffff)) * 16777619u;
    return hash;
}

/* Split alpha mask, asymmetric BGRA tint, a rotated quad, repeated use of
 * the same texture address after a guest edit, and padded guest scanlines. */
static void check_menu_overlay(void)
{
    enum { STRIDE = 768, DIM = 256 };
    static uint8_t texture[DIM*DIM];
    static uint32_t surface[NGB_SCAN_H][STRIDE];
    const uint32_t base = 0x40302010u;
    for (unsigned y=0; y<NGB_SCAN_H; ++y)
        for (unsigned x=0; x<STRIDE; ++x) surface[y][x]=base;
    /* In a square Morton texture, bit 14 is bit 7 of x. */
    for (unsigned i=0; i<sizeof(texture); ++i) texture[i] = (i & 0x4000) ? 255 : 0;
    struct screen_vertex v[] = {
        {64,32,0,1,0xff2468acu,0,0}, {192,96,0,1,0xff2468acu,1,0},
        {32,96,0,1,0xff2468acu,0,1}, {160,160,0,1,0xff2468acu,1,1},
    };
    ngb_menu_gpu_enable();
    CHECK(ngb_menu_gpu_overlay(v,texture,DIM,DIM,surface[0],STRIDE,NGB_SCAN_W,NGB_SCAN_H,0));
    ngb_menu_gpu_sync(&surface[90][135],4);
    CHECK(surface[90][135] == v[0].color && surface[80][72] == base);
    CHECK(surface[20][100] == base && surface[90][725] == base);
    memset(texture,128,sizeof(texture));
    for (unsigned i=0; i<4; ++i) v[i].color=0x804080c0;
    CHECK(ngb_menu_gpu_overlay(v,texture,DIM,DIM,surface[0],STRIDE,NGB_SCAN_W,NGB_SCAN_H,1));
    ngb_menu_gpu_flush();
    /* 128/255 mask times 128/255 tint alpha, then additive blending. */
    CHECK(surface[80][72] == 0x50404040u);
    CHECK(surface[90][725] == base);
    ngb_menu_gpu_close();
}

/* Follow the guest's idle timer and sample a grid excluding the blinking prompt.
 * Require sustained, moving scenery and a recognizable return to the same title. */
static void check_idle_scene(uint32_t physical)
{
    static uint32_t title[24*20], previous[24*20];
    static unsigned scene_frames, sampled;
    static uint64_t next_sample, release_at;
    const char *mode = getenv("NGB_TEST_IDLE_SCENE");
    uint64_t now = ngb_elapsed_ns() / 1000000;
    if (release_at && now >= release_at) {
        ngb_ohci_pad_sample(0,0,0,0,0);
        release_at = 0;
    }
    if (now < next_sample) return;
    next_sample = now + 120;
    const uint32_t *pixels = ngb_contiguous_pointer_raw(0x80000000u + physical, 3072*NGB_SCAN_H);
    CHECK(pixels);
    if (!sampled && (ngb_scene_active || frame_signature(pixels,103,621,11,142,341,13) != 0xa0a5912du)) return;
    pixels = ngb_scanout_last_pixels();
    CHECK(pixels);
    unsigned different = 0, moving = 0, colored = 0;
    for (unsigned i = 0; i < 24*20; ++i) {
        uint32_t rgb = pixels[(20+(i/24)*17)*NGB_SCAN_W + 12+(i%24)*26] & 0xffffff;
        if (!sampled) title[i] = rgb;
        unsigned delta = 0, change = 0;
        for (unsigned shift = 0; shift < 24; shift += 8) {
            int component = (rgb >> shift) & 255;
            delta += abs(component - (int)((title[i] >> shift) & 255));
            change += abs(component - (int)((previous[i] >> shift) & 255));
        }
        different += delta > 60;
        moving += change > 15;
        colored += (rgb & 0xff) > 48;
        previous[i] = rgb;
    }
    if (!sampled++) puts("[TEST] idle on original PRESS START");
    if (!ngb_scene_active) return;
    if (different > 300 && moving > 25 && colored > 80 && scene_frames < 8) {
        if (++scene_frames == 8) {
            puts("[TEST] original idle scene moving");
            benchmark_motion = 1;
            if (!strcmp(mode, "skip")) {
                ngb_ohci_pad_sample(16,0,0,0,0);
                release_at = now + 200;
            }
        }
    } else if (scene_frames == 8 && !release_at && different < 12) {
        ngb_stop("verified idle demo returned to title", !strcmp(mode, "skip"));
    }
}

#include "story_test.inc"

static void check_title_input(uint32_t physical)
{
    static unsigned phase;
    static uint64_t due;
    uint64_t now = ngb_elapsed_ns() / 1000000;
    if (now < due) return;
    if (phase>=4 && getenv("NGB_TEST_STORY")) { check_story_pad(physical,now); return; }
    const uint32_t *pixels = ngb_contiguous_pointer(0x80000000u + physical, 3072*NGB_SCAN_H);
    CHECK(pixels);
    switch (phase) {
    case 0:
        if (frame_signature(pixels,103,621,11,142,341,13) != 0xa0a5912du) return;
        CHECK(startup_deadline == 0 && !startup_expired());
        puts("[TEST] visible original title logo");
        due = now + 1700;
        break;
    case 1:
        ngb_ohci_pad_sample(16,0,0,0,0);
        due = now + 180;
        break;
    case 2:
        ngb_ohci_pad_sample(0,0,0,0,0);
        break;
    case 3:
        if (menu_cursor != 0 || frame_signature(pixels,190,535,8,36,70,5) != 0x86badb68u) return;
        puts("[TEST] visible original main menu");
        due = now + 1800;
        break;
    case 4:
        /* Both samples arrive before the next guest poll on a slow frame. */
        ngb_ohci_pad_sample(2,0,0,0,0);
        ngb_ohci_pad_sample(0,0,0,0,0);
        due = now + 250;
        break;
    case 5:
        ngb_ohci_pad_sample(0,0,0,0,0);
        due = now + 500;
        break;
    default:
        if (menu_cursor > 0 && menu_cursor < 8 &&
            frame_signature(pixels,190,535,8,36,70,5) == 0x86badb68u)
            ngb_stop("verified navigable main menu",menu_cursor);
        if (menu_cursor == 0) {
            phase = 4;
            due = now + 600;
        }
        return;
    }
    ++phase;
}

void __real_ngb_scanout_refresh(uint32_t);
void __wrap_ngb_scanout_refresh(uint32_t physical)
{
    __real_ngb_scanout_refresh(physical);
    if (getenv("NGB_TEST_IDLE_SCENE") && ngb_scanout_ready()) check_idle_scene(physical);
    if ((getenv("NGB_TEST_TITLE_MENU") || getenv("NGB_TEST_STORY")) && ngb_scanout_ready()) check_title_input(physical);
    if (!test_movie_frames || test_movie_address!=physical || !getenv("NGB_TEST_MOVIE_FRAME")) return;
    /* Observe the guest display surface after its flip, excluding row padding. */
    const uint32_t *src=ngb_contiguous_pointer(0x80000000u+physical,3072u*NGB_SCAN_H);
    CHECK(src);
    unsigned bright=0;
    uint32_t hash=2166136261u;
    for (unsigned y=0;y<NGB_SCAN_H;y++) {
        for (unsigned x=0;x<NGB_SCAN_W;x++) {
            uint32_t rgb=src[y*768+x]&0xffffff;
            bright += (rgb&255)>48;
            hash=(hash^rgb)*16777619u;
        }
    }
    if (bright<4096) return;
    if (getenv("NGB_TEST_MOVIE_MOTION")) {
        static uint32_t hashes[120];
        static unsigned count, last_draw;
        if (last_draw==(unsigned)test_movie_frames) return;
        last_draw=test_movie_frames;
        for (unsigned i=0;i<count;i++) if (hashes[i]==hash) return;
        hashes[count++]=hash;
        if (count==1 || count==30 || count==120)
            printf("[TEST] distinct movie scanouts=%u draw=%u hash=%08x\n",count,last_draw,hash);
        if (count<120) return;
    }
    const char *path=getenv("NGB_CAPTURE_MOVIE_PPM");
    if (path) {
        FILE *f=fopen(path,"wb"); CHECK(f);
        fprintf(f,"P6\n%u %u\n255\n",NGB_SCAN_W,NGB_SCAN_H);
        for (unsigned y=0;y<NGB_SCAN_H;y++) {
            unsigned char row[NGB_SCAN_W*3];
            for (unsigned x=0;x<NGB_SCAN_W;x++) {
                uint32_t c=src[y*768+x];
                row[3*x]=c>>16; row[3*x+1]=c>>8; row[3*x+2]=c;
            }
            CHECK(fwrite(row,1,sizeof(row),f)==sizeof(row));
        }
        CHECK(!fclose(f));
    }
    printf("[TEST] movie scanout frames=%u bright=%u hash=%08x\n",test_movie_frames,bright,hash);
    ngb_stop("verified visible movie frame",physical);
}
static int slow_enumeration, delay_instance_clear, delay_usb_enumeration, advance_vblank, inspect_fifo;

/* Host-only inspection of contiguous, linear packets. Never execute a
 * command here or change GET; control flow and split packets end the scan. */
static void trace_fifo(uint32_t put)
{
    uint32_t get = ngb_bus_read32(0xfd003244);
    uint32_t slot = ngb_bus_read32(0xfd00322c) & 0xffff, desc[3];
    void *obj = ngb_instance_aperture(NGB_PRAMIN_BASE + slot*16, sizeof(desc));
    if (!obj || put <= get || (put-get) % 4 || put-get > 64*1024) return;
    memcpy(desc, obj, sizeof(desc));
    uint64_t base = (desc[2] & 0xfffff000u) | (desc[0] >> 20);
    if ((uint64_t)put > (uint64_t)desc[1]+1 || base + put > 0x08000000u) return;
    const unsigned char *buf = ngb_contiguous_pointer(0x80000000u + base + get, put-get);
    if (!buf) return;
    unsigned pos = 0, packets = 0;
    while (pos < put-get) {
        uint32_t word;
        memcpy(&word, buf+pos, 4);
        uint32_t type = word & 0xe0030003u, count = (word >> 18) & 0x7ff;
        if ((type && type != 0x40000000u) || 4 + 4*count > put-get-pos) break;
        printf("[FIFO-HEADER] addr=%08x sub=%u method=%04x args=%u increment=%u\n",
               get+pos, word>>13 & 7, word & 0x1ffc, count, !type);
        /* CLEAR_SURFACE often sits inside an incrementing packet whose
         * header names the preceding clear-value register. */
        if (((word >> 13) & 7) == 0) {
            for (unsigned i = 0; i < count; ++i) {
                uint32_t m = ((word & 0x1ffcu) + (type ? 0 : 4*i)) & 0x1ffcu;
                if (m != 0x1d94 && getenv("NGB_TEST_FIFO_VALUES")) {
                    uint32_t value; memcpy(&value, buf+pos+4+4*i, 4);
                    printf("[METHOD] at=%08x m=%04x v=%08x\n", get+pos+4+4*i, m, value);
                }
                if (m != 0x1d94) continue;
                uint32_t mask;
                memcpy(&mask, buf+pos+4+4*i, 4);
                printf("[FIFO-SCAN] clear argument at=%08x mask=%08x\n", get+pos+4+4*i, mask);
            }
        }
        pos += 4 + 4*count;
        ++packets;
    }
    printf("[FIFO-SCAN] from=%08x to=%08x bytes=%u packets=%u\n", get, put, pos, packets);
}
/* One short physical tap during fade-in, even before input is unlocked. */
static void sample_warning_start(void)
{
    static uint64_t next_sample;
    static int pressed;
    uint64_t now = ngb_elapsed_ns() / 1000000;
    if (now < next_sample || !ngb_scanout_ready()) return;
    if (pressed) {
        ngb_ohci_pad_sample(0,0,0,0,0);
        test_start_button = 0;
        return;
    }
    next_sample = now + 30;
    uint32_t frame[72][128];
    ngb_scanout_blit(&frame[0][0],128,128,72);
    unsigned lit = 0;
    for (unsigned y=9;y<60;y++)
        for (unsigned x=25;x<100;x++) lit += (frame[y][x] & 255) > 8;
    if (lit > 20) {
        ngb_ohci_pad_sample(16,0,0,0,0);
        pressed = 1;
        next_sample = now + 80;
        puts("[TEST] early physical Start tap");
    }
}

void __real_ngb_nv2a_write32(uint32_t va, uint32_t value);
void __wrap_ngb_nv2a_write32(uint32_t va, uint32_t value)
{
    if (delay_usb_enumeration && va==NGB_PRAMIN_BASE+NGB_INSTANCE_PADDING+0x1000) {
        struct timespec delay={0,25000000};
        CHECK(nanosleep(&delay,NULL)==0);
        delay_usb_enumeration=0;
        ngb_guest_polls=1023; ngb_poll();
    }
    if (slow_enumeration && va>=NGB_PRAMIN_BASE+NGB_INSTANCE_PADDING &&
        va<NGB_PRAMIN_BASE+NGB_INSTANCE_PADDING+0x5000 && !(va&255)) {
        struct timespec nap={0,2000000};
        nanosleep(&nap,NULL);
    }
    if (test_start_button && va == 0xfd800040) sample_warning_start();
    if (inspect_fifo && va == 0xfd800040) trace_fifo(value);
    __real_ngb_nv2a_write32(va, value);
    /* The context DPC reopens PGRAPH after loading channel zero. Expire a
     * display interval just after it has consumed the original startup FIFO. */
    if (advance_vblank && va == 0xfd400720 && value == 1 &&
        ngb_bus_read32(0xfd003244) == 0x06675280) {
        CHECK(read32(0x86674000) == 5);
        advance_vblank = 0;
        start_ns -= 20000000;
        CHECK(ngb_bus_read32(0xfd600100) & 1);
        note("[TEST] vblank after startup semaphore readback=5");
    }
    if (delay_instance_clear && va == NGB_PRAMIN_BASE + NGB_INSTANCE_PADDING) {
        delay_instance_clear = 0;
        struct timespec delay = {0, 150000000};
        CHECK(nanosleep(&delay, NULL) == 0);
    }
}

static void invoke(uint32_t ordinal, const uint32_t *args, unsigned count)
{
    uint32_t sp = BOOT_STACK_TOP - 0x100;
    g_esp = sp;
    write32(sp, 0x12345678);
    for (unsigned i = 0; i < count; ++i) write32(sp + 4 + i * 4, args[i]);
    pending_ordinal = ordinal;
    kernel_call();
    CHECK(g_esp == sp + 4 + count * 4);
}

static void check_local_time(void)
{
    const uint32_t type = 0x6800, size = 0x6804, image = 0x6900, user = 0x6b00;
    invoke(24, (uint32_t[]){0xffff, 0, image, 256, 0}, 5);
    CHECK(!g_eax);
    memset((void *)ngb_guest_pointer(user, 257), 0xa5, 257);
    write32(type, 0xdeadbeef);
    invoke(24, (uint32_t[]){0xff, type, user, 95, size}, 5);
    CHECK(g_eax == 0xc0000023u && read32(size) == 96);
    CHECK(read32(type) == 0xdeadbeef && MEM8(user) == 0xa5 && MEM8(user + 95) == 0xa5);
    /* XAPI gives the user-settings query a 256-byte buffer. */
    invoke(24, (uint32_t[]){0xff, type, user, 256, size}, 5);
    CHECK(!g_eax && read32(type) == 3 && read32(size) == 96);
    CHECK(!memcmp(ram + user, ram + image + 0x60, 96));
    for (unsigned i = 96; i < 256; ++i) CHECK(!MEM8(user + i));
    CHECK(MEM8(user + 256) == 0xa5);

    const uint32_t time = 0x6808, fields = 0x6820;
    const uint16_t leap_day[] = {2000, 2, 29, 12, 34, 56, 789, 2};
    const uint64_t ticks = 125963012967890000ull;
    memcpy(ram + time, &ticks, sizeof(ticks));
    MEM8(fields + 16) = 0xa5;
    invoke(305, (uint32_t[]){time, fields}, 2);
    CHECK(!memcmp(ram + fields, leap_day, sizeof(leap_day)) && MEM8(fields + 16) == 0xa5);

    /* Run the retail GetLocalTime path used by the Chapter 4 scene. It calls
     * both kernel services and reorders the fields for the game. */
    memset(ram + fields, 0xff, 16);
    ngb_graphics_guest_call(0x00329fcb, &fields, 1);
    CHECK(MEM16(fields) >= 1601 && MEM16(fields + 2) >= 1 && MEM16(fields + 2) <= 12);
    CHECK(MEM16(fields + 4) <= 6 && MEM16(fields + 6) >= 1 && MEM16(fields + 6) <= 31);
    CHECK(MEM16(fields + 8) < 24 && MEM16(fields + 10) < 60 && MEM16(fields + 12) < 60);
    CHECK(MEM16(fields + 14) < 1000 && MEM8(fields + 16) == 0xa5);
}

static void check_gpu_startup(void)
{
    ngb_nv2a_reset();
    CHECK(ngb_bus_read32(0xfd001804) == 0);
    ngb_bus_write32(0xfd001804, 4);
    ngb_bus_write32(0xfd600140, 1);
    CHECK(ngb_bus_read32(0xfd009140) == 0);
    ngb_bus_write32(0xfd009140, 1);
    CHECK(ngb_bus_read32(0xfd001804) == 4);
    CHECK(ngb_bus_read32(0xfd600140) == 1);
    CHECK(ngb_bus_read32(0xfd009140) == 1);
    ngb_nv2a_reset();
    CHECK(ngb_bus_read32(0xfd001804) == 0);
    CHECK(ngb_bus_read32(0xfd600140) == 0);
    CHECK(ngb_bus_read32(0xfd009140) == 0);
}

/* Consecutive indirect writes must address distinct words in the tile
 * mirror. A PGRAPH reset clears the mirror without losing PFB tile state. */
static void check_tile_mirror(void)
{
    ngb_bus_write32(0xfd000200, 0x1000);
    ngb_bus_write32(0xfd100240, 0x10001);
    ngb_bus_write32(0xfd400750, 0xea0010);
    ngb_bus_write32(0xfd400754, 0x10001);
    ngb_bus_write32(0xfd400754, 0x20001);
    ngb_bus_write32(0xfd400750, 0xea0010);
    CHECK(ngb_bus_read32(0xfd400754) == 0x10001);
    CHECK(ngb_bus_read32(0xfd400754) == 0x20001);
    CHECK(ngb_bus_read32(0xfd400750) == 0xea0018);
    ngb_bus_write32(0xfd000200, 0);
    ngb_bus_write32(0xfd400750, 0xea0010);
    CHECK(!ngb_bus_read32(0xfd400754) && ngb_bus_read32(0xfd100240) == 0x10001);
    ngb_nv2a_reset();
}

/* Submit a split packet through USER, using independent RAMHT entries for
 * the 3D object and its PCI semaphore. Check the actual bytes visible to
 * the CPU, both neighboring words, the GET cursor, and the constant bank. */
static void check_graph_dma(void)
{
    const uint32_t ap = NGB_PRAMIN_BASE, put = 0xfd800040;
    CHECK(ngb_instance_claim(0x4000));
    uint32_t buf = ngb_contiguous_allocate(4096, 0, UINT32_MAX, 0, 4);
    CHECK(buf);
    uint32_t phys = buf - 0x80000000u;
    ngb_nv2a_reset();
    ngb_bus_write32(0xfd000200, 0x1100);
    ngb_bus_write32(0xfd002210, 0x100);
    ngb_bus_write32(0xfd002504, 1);
    ngb_bus_write32(0xfd003204, 0x100);
    ngb_bus_write32(0xfd003200, 1);
    ngb_bus_write32(0xfd003220, 1);
    ngb_bus_write32(0xfd003250, 1);
    ngb_bus_write32(0xfd400720, 1);
    ngb_bus_write32(0xfd400144, 0x10000);
    ngb_bus_write32(0xfd00322c, 0x1100);
    ngb_bus_write32(ap + 0x11000, 2);
    ngb_bus_write32(ap + 0x11004, 4095);
    ngb_bus_write32(ap + 0x11008, phys | 3);
    ngb_bus_write32(ap + 0x10008, 1);
    ngb_bus_write32(ap + 0x1000c, 0x80011101);
    ngb_bus_write32(ap + 0x11010, 0x97);
    ngb_bus_write32(ap + 0x10010, 2);
    ngb_bus_write32(ap + 0x10014, 0x80001102);
    ngb_bus_write32(ap + 0x11020, 0x0002003d);
    ngb_bus_write32(ap + 0x11024, 4095);
    ngb_bus_write32(ap + 0x11028, phys | 3);
    const uint32_t words[] = {
        0x40000, 1, 0x401a4, 2, 0x41ea4, 60,
        0x100b80, 1, 2, 3, 4, 0x81d6c, 0x104, 0xdead1234
    };
    for (unsigned i = 0; i < sizeof(words)/4; ++i) write32(buf+4*i, words[i]);
    for (unsigned i = 0; i < 3; ++i) write32(buf+0x100+4*i, 0xcdcdcdcd);
    ngb_bus_write32(put, 9*4);
    CHECK(ngb_bus_read32(put+4) == 36 && ngb_bus_read32(0xfd003228) == (2u<<18 | 0xb88));
    ngb_bus_write32(put, sizeof(words)-4);
    CHECK(read32(buf + 0x104) == 0xcdcdcdcd);
    ngb_bus_write32(put, sizeof(words));
    CHECK(ngb_bus_read32(put+4) == sizeof(words) && read32(buf + 0x104) == 0xdead1234);
    CHECK(read32(buf + 0x100) == 0xcdcdcdcd && read32(buf + 0x108) == 0xcdcdcdcd);
    ngb_bus_write32(0xfd400750, 0x170000 + 60*16);
    for (uint32_t v = 4; v; --v) CHECK(ngb_bus_read32(0xfd400754) == v);
    CHECK(ngb_bus_read32(0xfd400fc4) == 61u<<8);
    CHECK(ngb_bus_read32(0xfd003280) == 1);
#ifdef NGB_DIRECT3D
    /* Active HLE consumes these state packets in one pass. Stop at a
     * partial semaphore packet, then let its final word reach guest RAM. */
    const uint32_t material[] = {
        0x41ea4, 64, 0x100b80, 7, 8, 9, 10, 0x81b00, 12, 13,
        0x81d6c, 0x104, 0xbb441234
    };
    for (size_t i = 0; i < sizeof(material)/4; ++i)
        write32(buf + sizeof(words) + 4*i, material[i]);
    unsigned end = sizeof(words) + sizeof(material);
    ngb_scene_active = 1;
    uint64_t batched = ngb_direct_fifo_batched_words();
    ngb_bus_write32(put, end - 4);
    CHECK(ngb_direct_fifo_batched_words() == batched + 7);
    CHECK(ngb_bus_read32(put+4) == end - 4 && read32(buf+0x104) == 0xdead1234);
    CHECK(ngb_bus_read32(0xfd003228) == (1u<<18 | 0x1d70));
    ngb_bus_write32(put, end);
    CHECK(ngb_bus_read32(put+4) == end && read32(buf+0x104) == 0xbb441234);
    ngb_scene_active = 0;
#endif
    ngb_nv2a_reset();
    ngb_contiguous_reset();
}

/* Use colored input: a cleared black frame alone cannot expose a channel swap
 * or a mistaken pitch. Check clipping, channel masks, padding and scanout lifetime. */
static void check_clear_scanout(void)
{
    const unsigned pitch=3072, bytes=pitch*480, stride=1284;
    const uint32_t pattern=0xaabbccdd;
    CHECK(ngb_instance_claim(0x4000));
    uint32_t buf=ngb_contiguous_allocate(bytes,0,UINT32_MAX,0,4);
    CHECK(buf);
    uint32_t phys=buf-0x80000000u, *src=ngb_contiguous_pointer(buf,bytes);
    CHECK(src);
    for (unsigned i=0;i<bytes/4;i++) src[i]=pattern;
    uint32_t *desc=ngb_instance_aperture(NGB_PRAMIN_BASE+0x11000,12);
    CHECK(desc);
    desc[0]=0x3d; desc[1]=bytes-1; desc[2]=phys|3;
    static uint32_t regs[0x2000/4];
    const uint32_t settings[][2]={{0x194,0x11000},{0x200,720u<<16},{0x204,480u<<16},
        {0x208,0x128},{0x20c,pitch|(pitch<<16)},{0x210,0},{0x1d90,0x12345678},
        {0x1d98,1|(2u<<16)},{0x1d9c,1|(2u<<16)},{0x1d94,0x50}};
    for (unsigned i=0;i<sizeof(settings)/sizeof(settings[0]);i++)
        ngb_pgraph_method(regs,0x97,settings[i][0],settings[i][1]);
    for (unsigned y=0;y<480;y++) for (unsigned x=0;x<pitch/4;x++)
        CHECK(src[y*pitch/4+x]==((x>=1 && x<=2 && y>=1 && y<=2)?0xaa34cc78:pattern));
    src[0]=0x00112233; src[479*pitch/4+719]=0x99445566;
    ngb_scanout_reset();
    ngb_scanout_mode(0x0802020e,0x12,pitch,phys);
    CHECK(ngb_scanout_ready());
    unsigned gen=ngb_scanout_generation();
    ngb_scanout_refresh(phys);
    CHECK(ngb_scanout_generation()==gen);
    src[0]++;
    ngb_scanout_refresh(phys);
    CHECK(ngb_scanout_generation()!=gen);
    src[0]--;
    ngb_scanout_refresh(phys);
    ngb_contiguous_reset();
    uint32_t *out=calloc(stride*720,sizeof(*out));
    CHECK(out);
    ngb_scanout_blit(out,stride,1280,720);
    CHECK(out[0]==0xff332211 && out[719*stride+1279]==0xff665544);
    CHECK(out[2*stride+2]==0xff78cc34 && !out[719*stride+1280]);
    ngb_scanout_blank(1);
    ngb_scanout_blit(out,stride,1280,720);
    CHECK(out[0]==0xff000000 && out[719*stride+1279]==0xff000000);
    ngb_scanout_blank(0);
    ngb_scanout_blit(out,stride,1280,720);
    CHECK(out[0]==0xff332211);
    free(out);
    ngb_scanout_reset(); ngb_nv2a_reset();
}

static void check_gpu_clocks(void)
{
    const uint32_t enable = 0xfd000200u, timer = 0xfd009000u;
    CHECK(ngb_bus_read32(enable) == 0);
    ngb_bus_write32(enable, 0xffffffffu);
    CHECK(ngb_bus_read32(enable) == 0x01111100u);
    CHECK(ngb_nv2a_read8(0xfd680501) == 0x1c && ngb_nv2a_read8(0xfd680509) == 0xc2);
    CHECK(ngb_nv2a_read8(0xfd680505) == 0);
    ngb_bus_write32(timer + 0x200, 0xde86);
    ngb_bus_write32(timer + 0x210, 0x1dcd);
    CHECK(ngb_bus_read32(timer + 0x200) == 0xde86 && ngb_bus_read32(timer + 0x210) == 0x1dcd);
    /* Freeze the counter while setting a match 256 ticks in the future. */
    ngb_bus_write32(timer + 0x210, 0);
    uint32_t before = ngb_bus_read32(timer + 0x400);
    ngb_bus_write32(timer + 0x420, before + 8192 + 31);
    CHECK(ngb_bus_read32(timer + 0x420) == before + 8192);
    ngb_bus_write32(timer + 0x140, 1);
    ngb_bus_write32(0xfd000140, 1);
    CHECK(!ngb_nv2a_irq_pending());
    ngb_bus_write32(timer + 0x210, 0x1dcd);
    start_ns -= 1000000;
    CHECK(ngb_nv2a_irq_pending() == 1u << 20 && ngb_bus_read32(timer + 0x100) == 1);
    ngb_bus_write32(timer + 0x100, 1);
    CHECK(!ngb_nv2a_irq_pending());
    ngb_bus_write32(enable, 0);
    CHECK(ngb_bus_read32(timer + 0x400) == 0 && ngb_bus_read32(timer + 0x200) == 1);
    ngb_nv2a_reset();
}

/* Exercise the actual guest ISR after setting the driver's ready flag.
 * Keep IRQL at DPC level until its queued work has been inspected. */
static void check_gpu_interrupt(void)
{
    const uint32_t ctx = 0x7400, object = 0x7700, dpc = ctx + 0x84;
    uint32_t irq_args[] = {object, 0x003cf980, ctx, 0x33, 24, 0, 0};
    uint32_t dpc_args[] = {dpc, 0x003cfaa0, ctx};
    invoke(109, irq_args, 7);
    invoke(107, dpc_args, 3);
    write32(ctx, 0xfd000000);
    write32(ctx + 0xa0, 1);
    invoke(98, &object, 1); CHECK(g_eax && gpu_interrupt == object);
    invoke(98, &object, 1); CHECK(!g_eax);

    /* Advance the boot clock past a scan interval without a wall-clock wait. */
    ngb_bus_write32(0xfd000200, 1u << 24);
    start_ns -= 20000000;
    CHECK(!ngb_nv2a_irq_pending() && ngb_bus_read32(0xfd600100) == 1);
    ngb_bus_write32(0xfd600140, 1);
    CHECK(!ngb_nv2a_irq_pending() && ngb_bus_read32(0xfd000100) == 0x01000000);
    ngb_bus_write32(0xfd000140, 1);
    CHECK(ngb_nv2a_irq_pending() == 0x01000000);
    MEM8(g_fs_base + 0x24) = 24;
    ngb_guest_polls=15; ngb_poll(); CHECK(!ngb_pending_dpcs);
    MEM8(g_fs_base + 0x24) = 2;
    ngb_guest_polls=15; ngb_poll();
    CHECK(ngb_pending_dpcs == 1 && dpc_queue[0] == dpc && MEM8(dpc + 2));
    CHECK(!ngb_bus_read32(0xfd000140) && !ngb_nv2a_irq_pending());
    CHECK(MEM8(g_fs_base + 0x24) == 2);
    ngb_bus_write32(0xfd600100, 1);
    invoke(100, &object, 1); CHECK(g_eax && !gpu_interrupt && !MEM8(object + 16));
    invoke(100, &object, 1); CHECK(!g_eax);
    ngb_pending_dpcs = 0;
    MEM8(g_fs_base + 0x24) = 0;
    ngb_nv2a_reset();
}

/* Compare the mapped-page matrix kernel with the original SSE lift. The
 * second run crosses a page and must use the latter, including when the
 * destination aliases an input. */
static void check_guest_vectors(void)
{
    RecompXmm value = { .u = { 0x00010203, 0x04050607, 0xffeeddcc, 0x7fc12345 } };
    const uint32_t addr = 0x9ff9; /* fixed image data spanning two pages */
    unsigned char saved[16];
    memcpy(saved, ngb_fast_ram + addr, sizeof(saved));
    XMM_STORE(addr, value);
    RecompXmm readback = XMM_MEM(addr);
    CHECK(!memcmp(&readback, &value, 16) && !memcmp(ngb_fast_ram + addr, &value, 16));
    memcpy(ngb_fast_ram + addr, saved, sizeof(saved));

    uint32_t base = 0, bytes = 8192;
    CHECK(!ngb_vm_allocate(&base, &bytes, 0, 0x3000, 4));
    for (unsigned offset = 4080; offset < 4097; ++offset) {
        unsigned char *dst = ngb_fast_ram + base + offset;
        memset(dst-1, 0x5a, 18);
        XMM_STORE(base + offset, value);
        readback = XMM_MEM(base + offset);
        CHECK(!memcmp(&readback, &value, 16) && !memcmp(dst, &value, 16));
        CHECK(dst[-1] == 0x5a && dst[16] == 0x5a);
    }
    uint32_t release = 0;
    CHECK(!ngb_vm_free(&base, &release, 0x8000));
}

static void check_matrix_product(void)
{
    uint32_t base = 0, bytes = 8192;
    CHECK(!ngb_vm_allocate(&base, &bytes, 0, 0x3000, 4));
    RecompRegs saved = g_regs;
    for (unsigned variant = 0; variant < 2; ++variant) {
        unsigned char expected[64];
        RecompXmm scratch[6];
        for (unsigned run = 0; run < 2; ++run) {
            uint32_t left = base + (run ? 4096 - 32 : 128), right = base + 512;
            uint32_t destination = variant ? left : right;
            for (unsigned i = 0; i < 16; ++i) {
                MEMF(left + 4*i) = ((int)(i*71 % 23) - 11) / 7.0f;
                MEMF(right + 4*i) = ((int)(i*29 % 13) - 6) / 11.0f;
            }
            g_esp = BOOT_STACK_TOP - 32;
            write32(g_esp + 4, destination);
            write32(g_esp + 8, left);
            write32(g_esp + 12, right);
            if (variant) sub_00328232(); else sub_003CC550();
            CHECK(g_esp == BOOT_STACK_TOP - 16 && g_ecx == destination);
            CHECK(g_eax == (variant ? destination : left));
            RecompXmm regs[] = {g_xmm0, g_xmm1, g_xmm2, g_xmm3, g_xmm4, g_xmm5};
            void *result = (void *)ngb_guest_pointer(destination, 64);
            if (!run) {
                memcpy(expected, result, sizeof(expected));
                memcpy(scratch, regs, sizeof(scratch));
            } else {
                CHECK(!memcmp(expected, result, sizeof(expected)));
                CHECK(!memcmp(scratch, regs, sizeof(scratch)));
            }
        }
    }
    bytes = 0;
    CHECK(!ngb_vm_free(&base, &bytes, 0x8000));
    g_regs = saved;
}

static void check_contiguous(void)
{
    uint32_t request[] = {38215680, 0, UINT32_MAX, 0, 4};
    invoke(166, request, 5);
    uint32_t first = g_eax;
    CHECK(first == 0x84000000u);
    uint32_t last = first + request[0] - 4;
    write32(first, 0xabcdabcd); write32(last, 0x12341234);
    uint32_t second_bytes = 2 * 1024 * 1024;
    invoke(165, &second_bytes, 1);
    uint32_t second = g_eax;
    CHECK(second == last + 4 && read32(second) == 0);
    write32(second, 0x43214321);
    CHECK(read32(first) == 0xabcdabcd && read32(last) == 0x12341234);
    CHECK(read32(0x10000) == 0x48454258);
    CHECK(!ngb_contiguous_pointer(last, 5));
    ngb_scene_active = 1;
    uint32_t page = ngb_contiguous_physical(first) >> 12;
    ngb_texture_dirty[page] = ngb_vertex_dirty[page] = 0;
    CHECK(ngb_guest_vector_page(first + 16) == ngb_contiguous_pointer_raw(first + 16, 16));
    CHECK(ngb_texture_dirty[page] && ngb_vertex_dirty[page]);
    CHECK(!ngb_guest_vector_page(first + 4090) && !ngb_guest_vector_page(last));
    ngb_scene_track_surface(ngb_contiguous_physical(first), 16, 1);
    ngb_scene_track_surface(ngb_contiguous_physical(first) + 16, 32, 1);
    CHECK(!ngb_guest_vector_page(first + 16));
    ngb_scene_track_surface(ngb_contiguous_physical(first), 16, -1);
    CHECK(!ngb_guest_vector_page(first + 16));
    ngb_scene_track_surface(ngb_contiguous_physical(first) + 16, 32, -1);
    CHECK(ngb_guest_vector_page(first + 16));
    ngb_scene_active = 0;
    invoke(173, &last, 1); CHECK(g_eax == last - 0x80000000u);
    const uint32_t query[] = {last, 0x6800};
    invoke(217, query, 2);
    CHECK(!g_eax && read32(0x6804) == first && read32(0x680c) == 4096);
    uint32_t change[] = {first+8191,2,0x404};
    invoke(182, change, 3);
    const uint32_t changed[] = {first+4097, 0x6800};
    invoke(217, changed, 2);
    CHECK(read32(0x6804)==first && read32(0x6808)==4 && read32(0x680c)==8192 && read32(0x6814)==0x404);
    invoke(179, &first, 1); CHECK(g_eax==4);
    invoke(180, changed, 1); CHECK(g_eax==request[0]);
    CHECK(!ngb_contiguous_protect(last,8,0x404));
    invoke(179, &last, 1); CHECK(g_eax==4);
    CHECK(!ngb_contiguous_free(first + 1));
    uint32_t pin[] = {first + 4095, 2, 0};
    invoke(175, pin, 3); CHECK(!ngb_contiguous_free(first));
    CHECK(!ngb_contiguous_pin(first, 3 * 4096, 1)); /* no partial unlock */
    CHECK(!ngb_contiguous_pin(last, 5, 0));
    pin[2] = 1; invoke(175, pin, 3);
    CHECK(!ngb_contiguous_pin(first, 1, 1));
    CHECK(!ngb_ram_span(first, 4) && !ngb_fast_page_bytes[first >> 12]);
    ngb_contiguous_map_guest_banks(1);
    CHECK(ngb_ram_span(first, 8) == ngb_contiguous_pointer_raw(first, 8));
    CHECK(ngb_fast_page_bytes[first >> 12] == 4096 && ngb_guest_scalar(first, 8) == (uintptr_t)ngb_ram_span(first, 8));
    CHECK(!ngb_ram_span(first + 4093, 8) && !ngb_ram_span(0xfd000000, 4));
    invoke(171, &first, 1); CHECK(!ngb_contiguous_pointer(first, 1));
    CHECK(!ngb_ram_span(first, 8) && !ngb_fast_page_bytes[first >> 12]);
    CHECK(!ngb_contiguous_pages[page]);
    invoke(166, request, 5);
    CHECK(ngb_contiguous_pages[page] == ngb_contiguous_pointer_raw(first, 1));
    CHECK(g_eax == first && read32(first) == 0 && read32(last) == 0);
    CHECK(ngb_ram_span(first, 8) == ngb_contiguous_pointer_raw(first, 8));
    CHECK(ngb_fast_page_bytes[first >> 12] == 4096 && ngb_guest_scalar(first, 8) == (uintptr_t)ngb_ram_span(first, 8));
    ngb_contiguous_map_guest_banks(0);
    CHECK(!ngb_ram_span(first, 8) && !ngb_fast_page_bytes[first >> 12]);
    CHECK(read32(second) == 0x43214321);
    CHECK(!ngb_contiguous_allocate(UINT32_MAX, 0, UINT32_MAX, 0, 4));
    CHECK(!ngb_contiguous_allocate(0, 0, UINT32_MAX, 0, 4));
    CHECK(!ngb_contiguous_allocate(1, 0, UINT32_MAX, 8191, 4));
    CHECK(!ngb_contiguous_allocate(4096, 0x7000001, 0x7000fff, 4096, 4));
    CHECK(ngb_contiguous_allocate(4096, 0x7000001, 0x7010fff, 65536, 4) == 0x87010000u);
    uint32_t wc[] = {4096, 0, UINT32_MAX, 4096, 0x404};
    invoke(166, wc, 5); CHECK(g_eax);
    uint32_t wc_info[] = {g_eax, 0x6800};
    invoke(217, wc_info, 2);
    CHECK(!g_eax && read32(0x6808) == 0x404 && read32(0x6814) == 0x404);
    ngb_contiguous_reset();
    CHECK(!ngb_contiguous_pointer(second, 1) && !ngb_contiguous_pointer(0x87010000u, 1));
}

static void check_audio_boot(void)
{
    uint32_t base=ngb_contiguous_allocate(8192,0,UINT32_MAX,4096,4);
    CHECK(base);
    uint32_t phys=ngb_contiguous_physical(base);
    ngb_audio_reset();
    ngb_ac97_write(0xfec0012c,4,2);
    CHECK(ngb_ac97_read(0xfec00130,4)==0x100);
    ngb_ac97_write(0xfec00130,4,0x100);
    CHECK(ngb_ac97_read(0xfec00130,4)==0x100);
    ngb_apu_write(0xfe802040,phys);
    write32(base,phys+4096);
    uint32_t command=base+4096+0x810;
    write32(command,3);
    ngb_audio_poll();
    CHECK(read32(command)==3);
    ngb_apu_write(0xfe83fffc,3);
    write32(command-4,0x11223344);
    write32(command+4,0xaabbccdd);
    ngb_audio_poll();
    CHECK(!read32(command) && read32(command-4)==0x11223344 && read32(command+4)==0xaabbccdd);
    write32(command,4);
    ngb_audio_poll();
    CHECK(read32(command)==4);
    ngb_apu_write(0xfe800000 + NV_PAPU_VPVADDR, phys);
    ngb_apu_write(0xfe800000 + NV_PAPU_FENADDR, phys+4096);
    ngb_apu_write(0xfe820000 + NV1BA0_PIO_SET_ANTECEDENT_VOICE, 1u<<16);
    ngb_apu_write(0xfe820000 + NV1BA0_PIO_SET_CURRENT_VOICE, 0);
    ngb_apu_write(0xfe820000 + NV1BA0_PIO_SET_VOICE_CFG_FMT, NV_PAVS_VOICE_CFG_FMT_LOOP);
    ngb_apu_write(0xfe820000 + NV1BA0_PIO_SET_VOICE_CFG_BUF_LBO, 256);
    ngb_apu_write(0xfe820000 + NV1BA0_PIO_SET_VOICE_CFG_BUF_EBO, 1023);
    ngb_apu_write(0xfe820000 + NV1BA0_PIO_VOICE_ON, 0);
    start_ns -= 32000000; /* Cross the inclusive loop end at 48 kHz. */
    ngb_audio_poll();
    uint32_t pos=read32(base+NV_PAVS_VOICE_PAR_OFFSET) & NV_PAVS_VOICE_PAR_OFFSET_CBO;
    CHECK(pos>=256 && pos<=1023);
    ngb_apu_write(0xfe820000 + NV1BA0_PIO_VOICE_PAUSE, NV1BA0_PIO_VOICE_PAUSE_ACTION);
    pos=read32(base+NV_PAVS_VOICE_PAR_OFFSET);
    start_ns -= 10000000;
    ngb_audio_poll();
    CHECK(read32(base+NV_PAVS_VOICE_PAR_OFFSET)==pos);
    ngb_apu_write(0xfe800000 + NV_PAPU_IEN, NV_PAPU_ISTS_GINTSTS|NV_PAPU_ISTS_FENINTSTS);
    ngb_apu_write(0xfe820000 + NV1BA0_PIO_VOICE_OFF, 0);
    CHECK(!(read32(base+NV_PAVS_VOICE_PAR_STATE) & NV_PAVS_VOICE_PAR_STATE_ACTIVE_VOICE));
    CHECK(MEM16(base+4096+16*MCPX_HW_NOTIFIER_BASE_OFFSET+14)==0x0101);
    CHECK(ngb_apu_read(0xfe800000+NV_PAPU_ISTS) & NV_PAPU_ISTS_GINTSTS);
    ngb_apu_write(0xfe800000+NV_PAPU_ISTS, NV_PAPU_ISTS_FENINTSTS|NV_PAPU_ISTS_FEVINTSTS);
    CHECK(!ngb_audio_irq(5));
    ngb_apu_write(0xfe800000 + NV_PAPU_FETFORCE1,NV_PAPU_FETFORCE1_SE2FE_IDLE_VOICE);
    ngb_apu_write(0xfe800000 + NV_PAPU_IEN,NV_PAPU_ISTS_GINTSTS|NV_PAPU_ISTS_FETINTSTS);
    ngb_audio_poll();
    CHECK(ngb_audio_irq(5) == NV_PAPU_ISTS_FETINTSTS);
    CHECK(ngb_apu_read(0xfe800000 + NV_PAPU_FEDECMETH) == SE2FE_IDLE_VOICE);
    CHECK(!ngb_apu_read(0xfe800000 + NV_PAPU_FEDECPARAM));
    CHECK(ngb_apu_read(0xfe800000 + NV_PAPU_NVL2D) == 0xffff);
    ngb_apu_write(0xfe800000 + NV_PAPU_FECTL,0);
    ngb_apu_write(0xfe800000 + NV_PAPU_ISTS,NV_PAPU_ISTS_FETINTSTS);
    /* Acknowledging the interrupt does not unlink a voice. */
    start_ns -= 1000000;
    ngb_audio_poll();
    CHECK(ngb_audio_irq(5) == NV_PAPU_ISTS_FETINTSTS);
    ngb_apu_write(0xfe800000 + NV_PAPU_TVL2D, 0xffff);
    ngb_apu_write(0xfe800000 + NV_PAPU_FECTL, 0);
    ngb_apu_write(0xfe800000 + NV_PAPU_ISTS, NV_PAPU_ISTS_FETINTSTS);
    start_ns -= 1000000;
    ngb_audio_poll();
    CHECK(!ngb_audio_irq(5));
    ngb_audio_reset();
    CHECK(!ngb_ac97_read(0xfec00130,4));
    ngb_contiguous_reset();
}

static void check_gpu_instance(void)
{
    const uint32_t top = 0x87ff0000, aperture = NGB_PRAMIN_BASE + NGB_INSTANCE_PADDING;
    const uint32_t size = 0x5000;
    uint32_t args[] = {size, 0x6860};
    invoke(168, args, 2);
    CHECK(g_eax == top && read32(args[1]) == NGB_INSTANCE_PADDING);
    CHECK(!ngb_contiguous_pointer(top, 1) && !ngb_contiguous_pointer(top - size - 1, 1));
    CHECK(!ngb_instance_aperture(aperture - 1, 1) && !ngb_instance_aperture(aperture + size, 4));
    ngb_bus_write32(aperture, 0x12345678);
    CHECK(read32(top - 64) == 0x12345678);
    write32(top - 128 + 4, 0x87654321);
    CHECK(ngb_bus_read32(aperture + 68) == 0x87654321);
    CHECK(ngb_instance_claim(UINT32_MAX) == top && read32(top - 64) == 0x12345678);
    CHECK(ngb_instance_claim(0x40000) == 0 && read32(top - 64) == 0x12345678);
    CHECK(!ngb_contiguous_allocate(4096, 0x07fef000, UINT32_MAX, 0, 4));

    unsigned char *backing = ngb_contiguous_pointer(top - size, size);
    CHECK(backing);
    memset(backing, 0xa5, size);
    RecompRegs saved = g_regs;
    const uint32_t ctx = 0x9000;
    write32(ctx, 0xfd000000);
    g_esi = ctx;
    g_esp = BOOT_STACK_TOP - 0x100;
    PUSH32(g_esp, 0);
    sub_003D2DA6();
    CHECK(g_esp == BOOT_STACK_TOP - 0x100 && read32(ctx + 0x10) == top - size);
    CHECK(ngb_bus_read32(0xfd002210) == 0x03000100 && ngb_bus_read32(0xfd002214) == 0x00890110);
    for (size_t i = 0; i < size; ++i) CHECK(backing[i] == 0);
    g_regs = saved;

    uint32_t released = ngb_contiguous_allocate(4096, 0x07fea000, UINT32_MAX, 0, 4);
    CHECK(released == top - size - 4096 && !ngb_instance_claim(size + 4096));
    CHECK(ngb_contiguous_free(released) && ngb_instance_claim(size + 4096) == top);
    ngb_contiguous_reset();
    CHECK(!ngb_instance_aperture(aperture, 4));
    ngb_nv2a_reset();
}

static void check_memory_unit(void)
{
    const char name[] = "\\Device\\MU_0";
    memcpy((void *)ngb_guest_pointer(0x6800, sizeof(name)), name, sizeof(name));
    write32(0x6700, sizeof(name) << 16 | (sizeof(name) - 1)); write32(0x6704, 0x6800);
    uint32_t args[] = {0x3d9650, 368, 0x6700, 0x3a, 0, 0x6720};
    invoke(65, args, 6);
    uint32_t object = read32(0x6720), ext = read32(object + 0x18);
    CHECK(!g_eax && object && ext == object + 0x48);
    CHECK(read32(object) == (440u << 16 | 3) && read32(object + 8) == args[0]);
    CHECK(read32(object + 0x14) == 0x18 && MEM8(object + 0x1c) == 0x3a);
    CHECK(MEM8(object + 0x1d) == 0 && MEM8(object + 0x1e) == 1);
    CHECK(read32(object + 0x2c) == object + 0x2c && read32(object + 0x38) == 1);
    CHECK(read32(ext + 364) == 0); write32(ext + 364, 0x12345678);
    MEM8(0x6800 + 1) = 'd';
    invoke(65, args, 6); CHECK(g_eax == 0xc0000035 && read32(0x6720) == 0);
    CHECK(read32(ext + 364) == 0x12345678);
    args[1] = UINT32_MAX; invoke(65, args, 6);
    CHECK(g_eax == 0xc000000d && read32(0x6720) == 0);
    ngb_devices_reset();
}

static void check_usb_startup(void)
{
    uint32_t vector[] = {1, 0x6920};
    write32(vector[1], 0xfeedface);
    invoke(44, vector, 2);
    CHECK(g_eax == 0x31 && read32(vector[1]) == 0xfeedfa1a);
    vector[0] = 28;
    invoke(44, vector, 2);
    CHECK(!g_eax && read32(vector[1]) == 0xfeedfa1a);
    vector[0] = 9; vector[1] = 0;
    invoke(44, vector, 2); CHECK(g_eax == 0x39);

    const uint32_t object = 0x6900, args[] = {object, 0x3dfe3d, 0x80000784, 0x31, 26, 0, 0};
    write32(object + 0x70, 0xcafebabe);
    invoke(109, args, 7);
    CHECK(read32(object) == args[1] && read32(object + 4) == args[2]);
    CHECK(read32(object + 8) == 1 && read32(object + 12) == 26);
    CHECK(!read32(object + 16) && read32(object + 0x70) == 0xcafebabe);

    const uint32_t base = 0xfed00000;
    ngb_ohci_reset();
    CHECK(ngb_bus_read32(base) == 0x10 && ngb_bus_read32(base + 4) == 0);
    ngb_bus_write32(base + 0x48, 0x1200);
    CHECK(ngb_bus_read32(base + 0x48) == 0x1202);
    uint32_t va = ngb_contiguous_allocate(8192, 0, UINT32_MAX, 0, 4);
    CHECK(va != 0);
    uint32_t phys = ngb_contiguous_physical(va);
    ngb_bus_write32(base + 0x18, phys);
    CHECK(ngb_bus_read32(base + 0x18) == phys);
    ngb_bus_write32(base + 8, 1);
    CHECK(!ngb_bus_read32(base + 8) && !ngb_bus_read32(base + 0x18));
    CHECK(ngb_bus_read32(base + 4) == 0xc0 && ngb_bus_read32(base + 0x48) == 0x1202);
    ngb_bus_write32(va + 4, 0x13572468); CHECK(read32(va + 4) == 0x13572468);
    invoke(98, &object, 1); CHECK(g_eax && MEM8(object + 16));
    invoke(98, &object, 1); CHECK(!g_eax);
    ngb_ohci_pad_present(1);
    ngb_bus_write32(base + 4, 0x80);
    ngb_bus_write32(base + 0x10, 0x40);
    CHECK(ngb_ohci_irq_pending() == 0x40);
    ngb_bus_write32(base + 0x14, 0x80000000u);
    CHECK(!ngb_ohci_irq_pending() && (ngb_bus_read32(base + 0x0c) & 0x40));
    ngb_bus_write32(base + 0x10, 0x80000000u);
    CHECK(ngb_ohci_irq_pending() == 0x40);
    CHECK(ngb_bus_read32(base + 0x54) == 0x10101);
    ngb_bus_write32(base + 0x54, 0x10000);
    ngb_bus_write32(base + 0x0c, 0x40);
    CHECK(!ngb_ohci_irq_pending() && ngb_bus_read32(base + 0x54) == 0x101);
    /* A frame scheduled IN transfer must carry Start through the guest DMA
     * descriptor, including its completion, while a held WDH is respected. */
    const uint32_t ed = phys + 256, td = phys + 288, tail = phys + 304, buf = phys + 384;
    for (unsigned slot=0; slot<32; ++slot) write32(va+4*slot, ed);
    write32(va+256, 0x00201080); write32(va+260,tail); write32(va+264,td);
    write32(va+288, 0xf0040000); write32(va+292,buf);
    write32(va+296,tail); write32(va+300,buf+19);
    ngb_bus_write32(base+0x54,2); ngb_bus_write32(base+0x18,phys);
    ngb_bus_write32(base+4,0x84);
    ngb_ohci_pad_sample(16,0,0,0,0);
    start_ns -= 2000000;
    ngb_ohci_irq_pending();
    CHECK((read32(va+0x84)&~1u)==td && read32(va+384)==0x00101400);
    CHECK(!(read32(va+288)>>28) && !read32(va+292) && (read32(va+264)&~15u)==tail);
    write32(va+264,td); write32(va+292,buf); write32(va+296,tail);
    ngb_ohci_pad_sample(0,0,0,0,0);
    start_ns -= 2000000; ngb_ohci_irq_pending();
    CHECK(read32(va+292)==buf);
    ngb_bus_write32(base+0x0c,2);
    start_ns -= 2000000; ngb_ohci_irq_pending();
    CHECK(read32(va+384)==0x00001400 && !read32(va+292));
    ngb_ohci_pad_present(0); CHECK(ngb_ohci_irq_pending() == 0x40);
    invoke(100, &object, 1); CHECK(g_eax && !MEM8(object + 16));
    invoke(100, &object, 1); CHECK(!g_eax && !usb_interrupt);
    CHECK(ngb_contiguous_free(va));
    ngb_ohci_reset();
}

static void check_irql(void)
{
    invoke(129, NULL, 0); CHECK(!g_eax && MEM8(g_fs_base + 0x24) == 2);
    g_ecx = 3; invoke(160, NULL, 0); CHECK(g_eax == 2);
    invoke(103, NULL, 0); CHECK(g_eax == 3);
    const uint32_t timer[] = {0x6540, 0};
    invoke(113, timer, 2);
    CHECK(!ngb_timer_arm(timer[0], 0, 0, 0, 0));
    ngb_guest_polls = 1023; ngb_poll(); CHECK(!read32(timer[0] + 4));
    g_ecx = 0; invoke(161, NULL, 0);
    ngb_guest_polls = 1023; ngb_poll(); CHECK(read32(timer[0] + 4) == 1);
}

static void check_warning_input(int leave_via_logo)
{
    uint8_t report[20];
    ngb_ohci_pad_sample(0, 0, 0, 0, 0);
    ngb_ohci_reset();
    ngb_warning_file_read("demo.afs", 0x151000);
    ngb_pad_flip();
    CHECK(usb_gamepad_report(0, report, sizeof(report)) == 20 && !(report[2] & 16));
    ngb_ohci_pad_sample(16, 0, 0, 0, 0);
    ngb_ohci_pad_sample(0, 0, 0, 0, 0);
    ngb_pad_flip();
    CHECK(usb_gamepad_report(0, report, sizeof(report)) == 20 && (report[2] & 16));
    if (leave_via_logo) {
        ngb_pad_movie_input(1);
        ngb_pad_movie_input(0);
    } else ngb_warning_file_read("spr.afs", 0);
    for (unsigned i=0; i<16; ++i) {
        ngb_pad_flip();
        CHECK(usb_gamepad_report(0, report, sizeof(report)) == 20 && !(report[2] & 16));
    }
}

/* Make two parked workers compete for a turn. Read dispatcher signals
 * from current guest RAM: the game can set them without a kernel call. */
static void check_worker_reuse(void)
{
    RecompRegs initial=g_regs;
    uint32_t old_ordinal=pending_ordinal;
    CHECK(!thread_count && !retired);
    thread_count=1;
    const uint32_t args[]={0x6f00,0,0x4000,32,0x6f04,0,0,1,0,0x003298ad};
    invoke(255,args,10);
    uint32_t first=read32(args[0]), obj=workers[1].object;
    invoke(246,(uint32_t[]){first,0,0x6f08},3);
    CHECK(!g_eax && read32(0x6f08)==obj);
    write32(0x6f10,0);write32(0x6f14,0);
    invoke(234,(uint32_t[]){first,1,0,0x6f10},4);CHECK(g_eax==0x102);
    workers[1].exited=1; write32(obj+4,1);
    invoke(234,(uint32_t[]){first,1,0,0},4);CHECK(!g_eax);
    for (unsigned i=0;i<WORKER_LIMIT*2;i++) {
        invoke(255,args,10);
        uint32_t now=read32(args[0]);
        CHECK(now!=first && thread_count==2 && worker_handle(first) && read32(obj+4)==1);
        invoke(187,&now,1);CHECK(!g_eax);
        workers[1].exited=1;
    }
    invoke(233,(uint32_t[]){first,0,0},3);CHECK(!g_eax);
    invoke(187,&first,1);CHECK(!g_eax && !worker_handle(first));
    invoke(234,(uint32_t[]){first,1,0,0},4);CHECK(g_eax==NGB_FS_INVALID_HANDLE);
    invoke(246,(uint32_t[]){first,0,0x6f08},3);CHECK(g_eax==0xc0000008u);
    reap_thread_objects();CHECK(retired && read32(obj+4)==1);
    g_ecx=obj;invoke(250,NULL,0);reap_thread_objects();CHECK(!retired);
    uint32_t zero=0,base=workers[1].allocation;
    CHECK(!ngb_vm_free(&base,&zero,0x8000));
    reset_workers();thread_count=0;g_regs=initial;pending_ordinal=old_ordinal;
}

static void check_waiter_selection(void)
{
    unsigned count = thread_count;
    struct worker saved[3];
    memcpy(saved, workers, sizeof(saved));
    memset(workers, 0, sizeof(saved));
    thread_count = 3;
    CHECK(running_worker == 0);
    const uint32_t key = 0x5200007fu, event = 0x6680;
    struct named_event prior = events[127];
    uint32_t signal = read32(event + 4);
    events[127] = (struct named_event){key, 0, 0};
    workers[1].waiting = workers[1].wait_named = 1;
    workers[1].wait_key = key;
    workers[1].wait_until = 100;
    workers[2].waiting = 1;
    workers[2].wait_key = event;
    workers[2].wait_until = UINT64_MAX;
    write32(event + 4, 0);
    CHECK(next_worker(90) == 0);
    write32(event + 4, 1);
    CHECK(next_worker(90) == 2);
    CHECK(next_worker(100) == 1);
    events[127].token = 0;
    CHECK(next_worker(90) == 1);
    events[127].token = key;
    CHECK(ngb_io_event(key, 1) && next_worker(90) == 1);
    CHECK(ngb_io_event(key, 0));
    write32(event + 4, 0);
    workers[0].exited = 1;
    CHECK(next_worker(90) == 1);
    workers[1].suspended = 1;
    CHECK(next_worker(90) == 2);
    workers[0].exited = 0;
    workers[2].wait_key = NGB_VM_BEGIN; /* uncommitted: resume checked guest read */
    CHECK(next_worker(90) == 2);
    /* A finite wait after three minutes of play must time out normally.
     * Only bootstrap has a global deadline; use a synthetic start time so
     * this actually takes a millisecond rather than three minutes. */
    thread_count = 1;
    uint64_t saved_start = start_ns;
    const int64_t relative = -10000;
    memcpy((void *)ngb_guest_pointer(event + 8, 8), &relative, 8);
    start_ns -= BOOT_BUDGET_NS + 1000000;
    invoke(233, (uint32_t[]){key, 0, event + 8}, 3);
    CHECK(g_eax == 0x102);
    start_ns = saved_start;
    events[127] = prior;
    write32(event + 4, signal);
    thread_count = count;
    memcpy(workers, saved, sizeof(saved));
}

/* Exercise both event and file-handle completion through the retail kernel
 * entry points. Only the scheduler is allowed to publish into guest RAM. */
static void check_overlapped_reads(void)
{
    uint32_t file, information;
    CHECK(!ngb_file_open("D:\\default.xbe",0,0x80100080,3,1,0x48,&file,&information));
    invoke(189,(uint32_t[]){0x6820,0,1,1},4);
    uint32_t event=read32(0x6820);
    uint32_t args[]={file,event,0,0,0x6830,0x6840,4,0x6850};
    write32(0x6850,0); write32(0x6854,0);
    write32(0x6840,0xcccccccc); write32(0x6844,0xaaaaaaaa);
    invoke(219,args,8);
    CHECK(g_eax==NGB_FS_PENDING && read32(0x6830)==NGB_FS_PENDING && !read32(0x6834));
    CHECK(read32(0x6840)==0xcccccccc && !events[event&127].signalled);
    CHECK(ngb_file_wait_status(file)==NGB_FS_TIMEOUT);
    invoke(233,(uint32_t[]){file,0,0x6850},3);
    CHECK(g_eax==NGB_FS_TIMEOUT);
    invoke(233,(uint32_t[]){event,0,0},3);
    CHECK(!g_eax && !read32(0x6830) && read32(0x6834)==4 && read32(0x6840)==0x48454258);
    CHECK(!events[event&127].signalled && !ngb_file_wait_status(file));
    /* Back-to-back requests on one handle, a short final read, then EOF. */
    args[1]=0; write32(0x6850,4571134); write32(0x6840,0xa5a5a5a5);
    invoke(219,args,8); CHECK(g_eax==NGB_FS_PENDING);
    args[4]=0x6860; args[5]=0x6870; write32(0x6850,4571136); write32(0x6870,0x12345678);
    invoke(219,args,8); CHECK(g_eax==NGB_FS_PENDING);
    while (read32(0x6860)==NGB_FS_PENDING) ngb_io_yield();
    invoke(234,(uint32_t[]){file,1,0,0},4);
    CHECK(!g_eax && !read32(0x6830) && read32(0x6834)==2 && MEM16(0x6842)==0xa5a5);
    CHECK(read32(0x6860)==0xc0000011u && !read32(0x6864) && read32(0x6870)==0x12345678);
    /* Request without an event, waiting directly on the file. */
    write32(0x6850,0); invoke(219,args,8); CHECK(g_eax==NGB_FS_PENDING);
    invoke(234,(uint32_t[]){file,1,0,0},4);
    CHECK(!g_eax && !read32(0x6860) && read32(0x6870)==0x48454258);
    /* An explicit seek follows pending I/O on this handle. The next
     * current-position read must use the sought offset. */
    invoke(219,args,8); CHECK(g_eax==NGB_FS_PENDING);
    write32(0x6880,2); write32(0x6884,0);
    invoke(226,(uint32_t[]){file,0x6890,0x6880,8,14},5);
    CHECK(!g_eax && !read32(0x6860));
    args[7]=0; args[6]=2; invoke(219,args,8);
    CHECK(!g_eax && read32(0x6864)==2 && MEM16(0x6870)==0x4845);
    args[7]=0x6850; args[6]=4; args[1]=event;
    invoke(219,args,8); CHECK(g_eax==NGB_FS_PENDING);
    invoke(187,&event,1); CHECK(!g_eax);
    invoke(189,(uint32_t[]){0x6820,0,1,0},4);
    CHECK(!g_eax && read32(0x6820)!=event);
    event=read32(0x6820);
    while (ngb_pending_disc_reads) ngb_io_yield();
    CHECK(!events[event&127].signalled && !read32(0x6860));
    /* Close can race with the native reader. Once it returns the old request
     * must never write into storage reused by a new handle. */
    args[1]=event;
    invoke(219,args,8); CHECK(g_eax==NGB_FS_PENDING);
    invoke(187,&file,1); CHECK(!g_eax);
    CHECK(read32(0x6860)==0 || read32(0x6860)==0xc0000120u);
    CHECK(events[event&127].signalled);
    uint32_t replacement;
    CHECK(!ngb_file_open("D:\\default.xbe",0,0x80100080,3,1,0x48,&replacement,&information));
    CHECK(replacement!=file);
    write32(0x6870,0xabcdef01);
    while (ngb_pending_disc_reads) ngb_io_yield();
    CHECK(read32(0x6870)==0xabcdef01 && !ngb_file_wait_status(replacement));
    args[0]=replacement; args[1]=0;
    invoke(219,args,8); CHECK(g_eax==NGB_FS_PENDING);
    ngb_devices_reset();
    CHECK(!ngb_pending_disc_reads && read32(0x6870)==0xabcdef01);
    invoke(187,&event,1); CHECK(!g_eax);
    invoke(187,&replacement,1); CHECK(!g_eax);
}

int main(int argc, char **argv)
{
    if (argc == 4 && (!strcmp(argv[1], "--start-button") || !strcmp(argv[1], "--usb-reset") || !strcmp(argv[1], "--usb-slow") || !strcmp(argv[1], "--graphics-vblank") || !strcmp(argv[1], "--fifo-trace"))) {
        char image[1024];
        CHECK(snprintf(image, sizeof(image), "%s/default.xbe", argv[2]) < (int)sizeof(image));
        CHECK(ngb_files_init(argv[2], argv[3]) == 0);
        ngb_ohci_pad_present(1);
        test_start_button = !strcmp(argv[1], "--start-button");
        const char *scene = getenv("NGB_TEST_IDLE_SCENE");
        benchmark_combat = scene && !strcmp(scene, "combat");
        benchmark_scene = scene && !strcmp(scene, "benchmark");
        slow_enumeration = !strcmp(argv[1], "--usb-slow");
        delay_instance_clear = slow_enumeration || !strcmp(argv[1], "--usb-reset");
        delay_usb_enumeration=delay_instance_clear;
        advance_vblank = !strcmp(argv[1], "--graphics-vblank");
        inspect_fifo = !strcmp(argv[1], "--fifo-trace");
        int result = ngb_boot(image, stdout);
        if (getenv("NGB_TEST_STORY")) return !story_verified;
        if (benchmark_combat) return !combat_verified;
        return result;
    }
    CHECK(argc == 2);
    boot_log = tmpfile();
    CHECK(boot_log);
    start_ns = now_ns();
    if (setjmp(stop_context)) {
        fprintf(stderr, "Unexpected runtime stop: %s\n", stopped_reason);
        return 1;
    }
    CHECK(load_image(argv[1]));
    ngb_vm_init(ram);
    g_fs_base = 0x4000;
    initialize_thread();
    check_waiter_selection();
    check_worker_reuse();
    check_guest_vectors();
    check_matrix_product();
    check_contiguous();
    check_audio_boot();
    check_gpu_instance();
    /* XAPI signs the post-intro data with SHA-1. Exercise the guest stack
     * ABI, incremental updates, and the twenty-byte digest boundary. */
    const uint32_t sha_ctx=0x6800, in=0x6900, digest=0x6940;
    const uint8_t abc_sha1[20]={0xa9,0x99,0x3e,0x36,0x47,0x06,0x81,0x6a,0xba,0x3e,
                                0x25,0x71,0x78,0x50,0xc2,0x6c,0x9c,0xd0,0xd8,0x9d};
    memcpy((void *)ngb_guest_pointer(in,3),"abc",3);
    memset((void *)ngb_guest_pointer(digest,21),0xa5,21);
    invoke(335,&sha_ctx,1);
    invoke(336,(uint32_t[]){sha_ctx,in,1},3);
    invoke(336,(uint32_t[]){sha_ctx,in+1,2},3);
    invoke(337,(uint32_t[]){sha_ctx,digest},2);
    CHECK(!memcmp((void *)ngb_guest_pointer(digest,20),abc_sha1,20) && MEM8(digest+20)==0xa5);
    memset((void *)ngb_guest_pointer(0x6900, 257), 0xa5, 257);
    invoke(24, (uint32_t[]){0xffff, 0x6800, 0x6900, 255, 0x6804}, 5);
    CHECK(g_eax == 0xc0000023u && read32(0x6804) == 256 && MEM8(0x6900) == 0xa5);
    invoke(24, (uint32_t[]){0xffff, 0x6800, 0x6900, 256, 0x6804}, 5);
    CHECK(!g_eax && read32(0x6800) == 3 && read32(0x6958) == 0x00400100 && MEM8(0x6a00) == 0xa5);
    check_local_time();
    check_usb_startup();
    CHECK(pin_image(0x45eff8,16,0) && pin_image(0x45eff8,16,1));
    CHECK(!pin_image(0x45eff8,16,1) && !pin_image(0x3fff000,16,0));
    check_gpu_startup();
    check_tile_mirror();
    check_graph_dma();
    check_clear_scanout();
    check_menu_overlay();
    CHECK(!ngb_view_action(true,false,false,false,true));
    CHECK(ngb_view_action(true,true,false,false,true)==SHOW_DETAILS);
    CHECK(ngb_view_action(true,false,false,true,false)==SHOW_DETAILS);
    CHECK(ngb_view_action(false,false,false,false,true)==EXIT_GAME);
    check_gpu_clocks();
    check_gpu_interrupt();
    check_irql();
    struct timespec before, after;
    CHECK(clock_gettime(CLOCK_REALTIME, &before) == 0);
    write32(0x6628, 0xa5a5a5a5);
    const uint32_t clock_args[] = {0x6620};
    invoke(128, clock_args, 1);
    CHECK(clock_gettime(CLOCK_REALTIME, &after) == 0);
    uint64_t ticks = read32(0x6620) | (uint64_t)read32(0x6624) << 32;
    CHECK(ticks >= 116444736000000000ull + (uint64_t)before.tv_sec * 10000000 + before.tv_nsec / 100);
    CHECK(ticks <= 116444736000000000ull + (uint64_t)after.tv_sec * 10000000 + after.tv_nsec / 100);
    CHECK(read32(0x6628) == 0xa5a5a5a5);
    uint32_t args[5] = {0x6600, 0, 0x6604, 0x3000, 4};
    write32(0x6600, 0); write32(0x6604, 4096);
    invoke(184, args, 5);
    CHECK(g_eax == 0 && read32(0x6600) == NGB_VM_BEGIN);
    write32(NGB_VM_BEGIN, 0x12345678);
    const uint32_t free_args[] = {0x6600, 0x6604, 0x4000};
    invoke(199, free_args, 3);
    CHECK(g_eax == 0 && !ngb_vm_access(NGB_VM_BEGIN, 4));
    args[3] = 0x1000;
    invoke(184, args, 5);
    CHECK(g_eax == 0 && read32(NGB_VM_BEGIN) == 0);

    /* NGB's original idle-shutdown DPC returns without a shutdown request
     * when its counter is zero. Exercise its actual guest calling convention. */
    const uint32_t dpc_args[] = {0x6500, 0x0032f740, 0};
    invoke(107, dpc_args, 3);
    const uint32_t timer_args[] = {0x6540, 0};
    invoke(113, timer_args, 2);
    write32(0xc0ecc8, 0);
    g_eax = 0x11111111; g_ebx = 0x22222222; g_ecx = 0x33333333;
    RecompRegs saved = g_regs;
    CHECK(ngb_timer_arm(0x6540, 0, 1, 0, 0x6500) == 0);
    delivering_callback = 1;
    ngb_timers_poll(1, fire_timer);
    CHECK(read32(0x6544) == 1 && MEM8(0x6543) == 0);
    CHECK(memcmp(&saved, &g_regs, sizeof(saved)) == 0);
    CHECK(read32(g_fs_base) == 0xffffffff);
    CHECK(ngb_timer_cancel(0x6540) == 0);
    /* Exercise the guest ABI, not just the native file helper: counted ANSI
     * names, output pointers, IOSB bounds and stdcall stack cleanup. */
    char data[] = "/tmp/ngb-bridge-XXXXXX", disc[1024], cleanup[1100];
    CHECK(mkdtemp(data));
    CHECK(strlen(argv[1]) < sizeof(disc));
    strcpy(disc, argv[1]);
    char *slash = strrchr(disc, '/'); CHECK(slash); *slash = 0;
    CHECK(ngb_files_init(disc, data) == 0);
    const char path[] = "D:\\default.xbe";
    memcpy((void *)ngb_guest_pointer(0x6800, sizeof(path)), path, sizeof(path));
    write32(0x6700, (sizeof(path) << 16) | (sizeof(path) - 1));
    write32(0x6704, 0x6800);
    write32(0x6710, 0); write32(0x6714, 0x6700); write32(0x6718, 0x40);
    write32(0x6738, 0xa5a5a5a5);
    const uint32_t open_args[] = {0x6720, 0x80000000, 0x6710, 0x6730, 3, 0x60};
    invoke(202, open_args, 6);
    CHECK(g_eax == 0 && read32(0x6730) == 0 && read32(0x6734) == 1);
    uint32_t file = read32(0x6720);
    const uint32_t read_args[] = {file, 0, 0, 0, 0x6730, 0x6740, 4, 0};
    write32(0x6744, 0xa5a5a5a5);
    invoke(219, read_args, 8);
    CHECK(g_eax == 0 && read32(0x6734) == 4 && read32(0x6740) == 0x48454258);
    CHECK(read32(0x6738) == 0xa5a5a5a5 && read32(0x6744) == 0xa5a5a5a5);
    const uint32_t query_args[] = {file, 0x6730, 0x6900, 24, 5};
    invoke(211, query_args, 5);
    CHECK(g_eax == 0 && read32(0x6734) == 24 && read32(0x6908) == 4571136);
    invoke(187, &file, 1); CHECK(g_eax == 0);
    invoke(219, read_args, 8);
    CHECK(g_eax == NGB_FS_INVALID_HANDLE && read32(0x6734) == 0);
    check_overlapped_reads();
    const char drive[] = "\\??\\z:";
    const char target[] = "\\Device\\Harddisk0\\Partition5";
    CHECK(ngb_file_link("\\??\\Z:", target) == 0);
    memcpy((void *)ngb_guest_pointer(0x6800, sizeof(drive)), drive, sizeof(drive));
    write32(0x6700, (sizeof(drive) << 16) | (sizeof(drive) - 1));
    const uint32_t open_link[] = {0x6720, 0x6710};
    write32(0x6718, 0);
    invoke(203, open_link, 2); CHECK(g_eax == 0xc0000034u && read32(0x6720) == 0);
    write32(0x6718, 0x40);
    invoke(203, open_link, 2); CHECK(g_eax == 0);
    uint32_t link = read32(0x6720);
    const uint32_t query_link[] = {link, 0x6750, 0x6760};
    write32(0x6754, 0x6800); write32(0x6750, (sizeof(target) - 1) << 16);
    invoke(215, query_link, 3);
    CHECK(g_eax == 0xc0000023u && read32(0x6760) == sizeof(target) - 1);
    CHECK(!memcmp((void *)ngb_guest_pointer(0x6800, sizeof(drive)), drive, sizeof(drive)));
    write32(0x6750, sizeof(target) << 16);
    MEM8(0x6800 + sizeof(target)) = 0xa5;
    invoke(215, query_link, 3);
    CHECK(g_eax == 0 && MEM16(0x6750) == sizeof(target) - 1);
    CHECK(!memcmp((void *)ngb_guest_pointer(0x6800, sizeof(target)), target, sizeof(target)));
    CHECK(MEM8(0x6800 + sizeof(target)) == 0xa5);
    invoke(187, &link, 1); CHECK(g_eax == 0);
    invoke(215, query_link, 3); CHECK(g_eax == NGB_FS_INVALID_HANDLE);
    uint32_t first_tick = read32(GUEST_TICK_COUNT);
    start_ns -= 3000000;
    CHECK(read32(GUEST_TICK_COUNT) - first_tick >= 3);
    check_warning_input(0);
    check_warning_input(1);
    check_memory_unit();
    ngb_files_close_all();
    snprintf(cleanup, sizeof(cleanup), "%s/hdd", data);
    CHECK(rmdir(cleanup) == 0 && rmdir(data) == 0);
    free(ram);
    fclose(boot_log);
    puts("Bridge ABI, guest file I/O, decommit/recommit and original game DPC/register restore passed");
    return 0;
}
