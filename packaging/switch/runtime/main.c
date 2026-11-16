#include "runtime.h"
#include "profile.h"
#include "frontend_input.h"
#include "scanout.h"
#include "files.h"
#include "ohci_boot.h"
#include <string.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdlib.h>
#include <sys/stat.h>

#ifdef __SWITCH__
#include <switch.h>
static atomic_bool finished;
static int boot_status;
static FILE *boot_log;
static const char *startup_error;
static atomic_bool input_stop, game_view, gameplay_controls;
void ngb_frontend_menu_controls(void) { atomic_store(&gameplay_controls,true); }
static atomic_uint commands;
static u64 launch_tick;

#ifdef NGB_DIRECT3D
/* Sample one thread at a time. Both profiles stay in RAM until exit. */
#include "direct/output.h"
extern char _start[];
/* Boundaries are guest flips, so light scenes cannot dilute combat samples. */
static const struct { unsigned first, last; } profile_windows[] = {
    {1, 120}, {121, 720}, {721, 840}, {1801, 1920}
};
#define PROFILE_WINDOWS (sizeof(profile_windows) / sizeof(profile_windows[0]))
static atomic_uint current_window; /* one-based; 0 means off */
static atomic_uint profile_frame, completed_windows;
static unsigned sampled_window; /* UI thread only */
enum { STACK_DEPTH = 48 };
typedef struct {
    uint32_t pc, lr, callers[STACK_DEPTH];
    unsigned scope, depth, frame, worker_id;
    uint64_t wall_tick, cpu_tick;
} StackSample;
typedef struct {
    StackSample samples[768];
    Result clock_error;
    unsigned count;
    uint64_t ticks;
    Result error;
} CpuProfile;
static CpuProfile guest_profiles[PROFILE_WINDOWS], render_profiles[PROFILE_WINDOWS];

/* The longest window is 600 frames. One boundary is shared by adjacent frames. */
typedef struct { uint64_t wall, cpu, entries, polls, switches, skips; unsigned draws; Result rc; } FrameMark;
static FrameMark frame_marks[PROFILE_WINDOWS][601];
static unsigned mark_count[PROFILE_WINDOWS];

static Result thread_ticks(Handle handle, u64 *value)
{
    return svcGetInfo(value, hosversionAtLeast(13, 0, 0) ? InfoType_ThreadTickCount :
                      InfoType_ThreadTickCountDeprecated, handle, TickCountInfo_Total);
}

void ngb_profile_next_frame(unsigned frame, unsigned draws)
{
    if (frame==1) atomic_store(&gameplay_controls,true);
    unsigned active = 0;
    FrameMark mark = {0};
    for (unsigned i = 0; i < PROFILE_WINDOWS; ++i) {
        unsigned first = profile_windows[i].first, last = profile_windows[i].last;
        if (frame < first || frame > last + 1) continue;
        if (!mark.wall) {
            mark.wall = armGetSystemTick();
            mark.rc = thread_ticks(threadGetSelf()->handle, &mark.cpu);
            mark.draws = draws;
            ngb_profile_work_counts(&mark.entries, &mark.polls, &mark.switches, &mark.skips);
        }
        unsigned index = frame - first;
        frame_marks[i][index] = mark;
        mark_count[i] = index + 1;
        if (frame <= last) active = i + 1;
        else atomic_store(&completed_windows, i + 1);
    }
    atomic_store(&profile_frame, frame);
    atomic_store(&current_window, active);
}

static uint32_t module_offset(uint64_t address)
{
    uintptr_t base = (uintptr_t)_start;
    return address >= base && address - base < UINT32_MAX ? (uint32_t)(address - base) : UINT32_MAX;
}

/* Unwind AAPCS64 frame records only within the paused thread's actual
 * stack. Cooperative Xbox threads and XAPI fibers have separate stacks. */
static void capture_callers(StackSample *sample, const ThreadContext *ctx, Thread *worker, bool guest)
{
    uintptr_t base = (uintptr_t)worker->stack_mirror;
    uintptr_t end = base && ctx->sp >= base && ctx->sp - base < worker->stack_sz ?
                    base + worker->stack_sz : 0;
    if (!end && guest) end = ngb_profile_fiber_stack_end(ctx->sp);
    uintptr_t fp = ctx->fp, floor = ctx->sp;
    while (end && fp >= floor && fp <= end - 16 && !(fp & 15) && sample->depth < STACK_DEPTH) {
        uintptr_t pair[2];
        memcpy(pair, (const void *)fp, sizeof(pair));
        if (pair[1] < 4 || (pair[1] & 3)) break;
        uint32_t caller = module_offset(pair[1] - 4);
        if (caller == UINT32_MAX) break;
        sample->callers[sample->depth++] = caller;
        floor = fp + 16;
        fp = pair[0];
    }
}

static void sample_thread(CpuProfile *profile, Thread *worker, bool guest)
{
    if (R_FAILED(profile->error) || profile->count >= sizeof(profile->samples)/sizeof(profile->samples[0])) return;
    StackSample *sample = &profile->samples[profile->count];
    uint64_t now = armGetSystemTick();
    ThreadContext ctx;
    profile->error = threadPause(worker);
    if (R_FAILED(profile->error)) return;
    profile->error = threadDumpContext(&ctx, worker);
    if (R_SUCCEEDED(profile->error)) {
        sample->wall_tick = now;
        sample->frame = atomic_load(&profile_frame);
        sample->scope = ngb_direct_sample_scope();
        sample->worker_id = guest ? ngb_profile_worker_id() : 0;
        sample->pc = module_offset(ctx.pc.x);
        sample->lr = module_offset(ctx.lr);
        sample->depth = 0;
        if (R_SUCCEEDED(profile->clock_error))
            profile->clock_error = thread_ticks(worker->handle, &sample->cpu_tick);
        capture_callers(sample, &ctx, worker, guest);
    }
    Result resumed = threadResume(worker);
    profile->ticks += armGetSystemTick() - now;
    if (R_FAILED(resumed)) profile->error = resumed;
    if (R_SUCCEEDED(profile->error)) ++profile->count;
}

static void sample_render_worker(void *worker) { sample_thread(&render_profiles[sampled_window], worker, false); }

/* Record the clock selected by the system during gameplay. This only reads
 * clkrst; absent service access must not interfere with the sampler. */
static void log_game_clocks(unsigned first_frame)
{
    Result rc = clkrstInitialize();
    if (R_FAILED(rc)) {
        fprintf(boot_log, "[CLOCK] first=%u unavailable=%08x\n", first_frame, rc);
        return;
    }
    const PcvModuleId modules[] = { PcvModuleId_CpuBus, PcvModuleId_GPU };
    u32 hz[2] = {0};
    for (unsigned i = 0; i < 2; ++i) {
        ClkrstSession session;
        if (R_SUCCEEDED(clkrstOpenSession(&session, modules[i], 3))) {
            clkrstGetClockRate(&session, &hz[i]);
            clkrstCloseSession(&session);
        }
    }
    clkrstExit();
    fprintf(boot_log, "[CLOCK] first=%u cpu_hz=%u gpu_hz=%u\n", first_frame, hz[0], hz[1]);
}

static void sample_guest_thread(Thread *worker)
{
    static uint64_t next_tick;
    unsigned w = atomic_load(&current_window);
    if (!w || atomic_load(&finished)) return;
    static unsigned clock_window;
    if (w != clock_window) {
        clock_window = w;
        log_game_clocks(profile_windows[w - 1].first);
    }
    sampled_window = w - 1;
    CpuProfile *guest = &guest_profiles[w-1], *render = &render_profiles[w-1];
    if (R_FAILED(guest->error) && R_FAILED(render->error)) return;
    uint64_t now = armGetSystemTick();
    if (now < next_tick) return;
    uint64_t interval_ms = profile_windows[w - 1].first == 1801 || profile_windows[w - 1].first == 1 ? 8 + guest->count % 7 : 45 + guest->count % 17;
    next_tick = now + armNsToTicks(interval_ms * 1000000);
    if (!envIsSyscallHinted(0x32) || !envIsSyscallHinted(0x33)) {
        guest->error = render->error = MAKERESULT(Module_Libnx, LibnxError_IncompatSysVer);
        return;
    }
    unsigned g = guest->count, r = render->count;
    sample_thread(guest, worker, true);
    ngb_direct_visit_worker(sample_render_worker);
    if (atomic_load(&current_window) != w) { guest->count = g; render->count = r; }
}

static void write_profile(const CpuProfile *profile, const char *header, const char *row)
{
    fprintf(boot_log, "[%s] samples=%u pause_us=%llu rc=%08x\n", header, profile->count,
            (unsigned long long)(armTicksToNs(profile->ticks) / 1000), profile->error);
    for (unsigned i = 0; i < profile->count; ++i) {
        if (i % 16 == 0) fputs(row, boot_log);
        fprintf(boot_log, " %08x/%08x", profile->samples[i].pc, profile->samples[i].lr);
        if (i % 16 == 15 || i + 1 == profile->count) fputc('\n', boot_log);
    }
}

static void write_callers(const CpuProfile *profile, const char *role)
{
    fprintf(boot_log, "[CALLERS] thread=%s clock_rc=%08x stack_limit=%u tick_hz=%llu\n",
            role, profile->clock_error, STACK_DEPTH, (unsigned long long)armGetSystemTickFreq());
    for (unsigned i = 0; i < profile->count; ++i) {
        const StackSample *s = &profile->samples[i];
        fprintf(boot_log, "[STACK] %u %u %u %llu %llu %08x", s->frame, s->worker_id, s->scope,
                (unsigned long long)s->wall_tick, (unsigned long long)s->cpu_tick, s->pc);
        for (unsigned j = 0; j < s->depth; ++j) fprintf(boot_log, " %08x", s->callers[j]);
        fputc('\n', boot_log);
    }
}

static void write_guest_samples(unsigned limit)
{
    if (!boot_log) return;
    static unsigned written;
    flockfile(boot_log);
    for (; written < limit; ++written) {
        unsigned i = written;
        if (!mark_count[i] && !guest_profiles[i].count && !render_profiles[i].count && !guest_profiles[i].error && !render_profiles[i].error) continue;
        fprintf(boot_log, "[PROFILE_WINDOW] first=%u last=%u\n", profile_windows[i].first, profile_windows[i].last);
        write_profile(&guest_profiles[i], "CPU", "[PC]");
        // Each digit labels the corresponding PC row entry. 0=other,
        // 1=mesh, 2=indexed. Bit 2 identifies material setter calls.
        fputs("[GUEST_SCOPE] ", boot_log);
        for (unsigned j = 0; j < guest_profiles[i].count; ++j)
            fputc('0' + guest_profiles[i].samples[j].scope, boot_log);
        fputc('\n', boot_log);
        write_profile(&render_profiles[i], "RENDER_CPU", "[RPC]");
        write_callers(&guest_profiles[i], "guest");
        write_callers(&render_profiles[i], "render");
        if (mark_count[i] >= 2) {
            FrameMark a = frame_marks[i][0], b = frame_marks[i][mark_count[i]-1];
            fprintf(boot_log, "[SCHED] first=%u frames=%u switches=%llu skipped_waiters=%llu\n",
                profile_windows[i].first, mark_count[i]-1,
                (unsigned long long)(b.switches-a.switches), (unsigned long long)(b.skips-a.skips));
        }
        for (unsigned j = 1; j < mark_count[i]; ++j) {
            FrameMark a = frame_marks[i][j-1], b = frame_marks[i][j];
            Result rc = R_FAILED(a.rc) ? a.rc : b.rc;
            fprintf(boot_log, "[FRAME_CPU] frame=%u wall_us=%llu guest_cpu_us=%llu rc=%08x draws=%u entries=%llu polls=%llu\n",
                profile_windows[i].first + j - 1, (unsigned long long)(armTicksToNs(b.wall-a.wall)/1000),
                (unsigned long long)(R_SUCCEEDED(rc) ? armTicksToNs(b.cpu-a.cpu)/1000 : 0), rc,
                b.draws - a.draws, (unsigned long long)(b.entries - a.entries),
                (unsigned long long)(b.polls - a.polls));
        }
    }
    fflush(boot_log);
    funlockfile(boot_log);
}
#endif

static void poll_input(PadState *pad);
static void input_worker(void *arg)
{
    PadState *pad = arg;
    while (!atomic_load(&input_stop)) {
        poll_input(pad);
        svcSleepThread(4000000);
    }
}

static void sample_pad(PadState *pad, bool game_input)
{
    static const uint64_t mapped[] = {
        HidNpadButton_Up,HidNpadButton_Down,HidNpadButton_Left,HidNpadButton_Right,
        HidNpadButton_Plus,HidNpadButton_Minus,HidNpadButton_StickL,HidNpadButton_StickR,
        HidNpadButton_A,HidNpadButton_B,HidNpadButton_X,HidNpadButton_Y,
        HidNpadButton_R,HidNpadButton_L,HidNpadButton_ZL,HidNpadButton_ZR
    };
    /* B opens the port diagnostics. Passing it through can also tear down
     * the guest movie while its decoder thread is running. */
    uint64_t held=padGetButtons(pad);
    if (!game_input || !atomic_load(&gameplay_controls)) held &= ~HidNpadButton_B;
    else if ((held & (HidNpadButton_Minus|HidNpadButton_B))==(HidNpadButton_Minus|HidNpadButton_B))
        held &= ~(HidNpadButton_Minus|HidNpadButton_B);
    if (!game_input) held &= ~HidNpadButton_Plus;
    uint16_t buttons=0;
    for (unsigned i=0;i<16;i++) if (held&mapped[i]) buttons|=1u<<i;
    HidAnalogStickState l=padGetStickPos(pad,0), r=padGetStickPos(pad,1);
    /* Saturate the negative extreme so that full stick never wraps. */
    ngb_ohci_pad_sample(buttons,l.x,l.y,
                        r.x <= -32768 ? 32767 : -r.x,
                        r.y <= -32768 ? 32767 : -r.y);
    ngb_ohci_pad_present(padIsConnected(pad));
}
/* Only the input owner reads libnx pad state. Button edges remain available
 * even while the UI is submitting a framebuffer or switching consoles. */
static void poll_input(PadState *pad)
{
    padUpdate(pad);
    bool game = atomic_load(&game_view);
    u64 down = padGetButtonsDown(pad);
    bool stopped = atomic_load(&finished);
    sample_pad(pad, game && !stopped);
    unsigned action = ngb_view_action(game,stopped,down & HidNpadButton_A,
                                     (down & HidNpadButton_B) && (!atomic_load(&gameplay_controls) || stopped ||
                                     (padGetButtons(pad)&HidNpadButton_Minus)),down & HidNpadButton_Plus);
    if (action) atomic_fetch_or(&commands, action);
    if (boot_log && (down & (HidNpadButton_B | HidNpadButton_Plus))) {
        fprintf(boot_log,"[INPUT] Plus=%d B=%d game_view=%d connected=%d stopped=%d uptime_ms=%llu\n",
                !!(down & HidNpadButton_Plus), !!(down & HidNpadButton_B), game, padIsConnected(pad), stopped,
                (unsigned long long)(armTicksToNs(armGetSystemTick()-launch_tick)/1000000));
        fflush(boot_log);
    }
}
static void guest_worker(void *arg)
{
    (void)arg;
    /* Retail levels read far beyond the attract-mode slices in RomFS.
     * Mount the user's extracted disc directly, without a second copy or
     * a persistent SD cache. ngb_boot validates the XBE against this lift. */
    static const char external[]="sdmc:/switch/ngb-runtime/disc";
    struct stat st;
    const char *image="sdmc:/switch/ngb-runtime/disc/default.xbe";
    fprintf(boot_log,"[DISC] source=%s\n",external);
    if (stat(image,&st) || !S_ISREG(st.st_mode)) {
        startup_error = "Copy the extracted game to /switch/ngb-runtime/disc (default.xbe missing)";
        fprintf(boot_log,"[ERROR] %s\n",startup_error);
        boot_status=NGB_BOOT_ERROR;
        fflush(boot_log);
    } else if (ngb_files_init(external, "sdmc:/switch/ngb-runtime/data")) {
        fprintf(boot_log, "[ERROR] virtual disk initialization failed\n");
        boot_status = NGB_BOOT_ERROR;
        startup_error = "virtual disk initialization failed";
        fflush(boot_log);
    } else boot_status = ngb_boot(image, boot_log);
    atomic_store(&finished, true);
}

int main(void)
{
    launch_tick=armGetSystemTick();
    consoleInit(NULL);
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    padUpdate(&pad);
    sample_pad(&pad, false);
    mkdir("sdmc:/switch", 0777);
    mkdir("sdmc:/switch/ngb-runtime", 0777);
    mkdir("sdmc:/switch/ngb-runtime/logs", 0777);
    const char *current_log = "sdmc:/switch/ngb-runtime/logs/boot.log";
    const char *previous_log = "sdmc:/switch/ngb-runtime/logs/boot.previous.log";
    struct stat last;
    if (!stat(current_log,&last) && last.st_size > 0) {
        remove(previous_log);
        rename(current_log,previous_log);
    }
    boot_log = fopen(current_log, "w");
#ifdef NGB_DIRECT3D
    if (boot_log) { fprintf(boot_log, "[CONFIG] kickoff_kib=%u\n", NGB_DIRECT_KICKOFF_KIB); fflush(boot_log); }
#endif
    Result rc = romfsInit();
    Thread worker, input;
    bool input_started = false;
    bool created = false, started = false;
    if (boot_log && R_SUCCEEDED(rc)) {
        u64 allowed = 0;
        u32 ui_core = svcGetCurrentProcessorNumber();
        s32 core = -2;
        if (R_SUCCEEDED(svcGetInfo(&allowed, InfoType_CoreMask, CUR_PROCESS_HANDLE, 0))) {
            u64 other = allowed & ~(1ull << ui_core);
            if (other) core = __builtin_ctzll(other);
        }
        /* Keep input responsive on hosts granting just the main core too. */
        rc = threadCreate(&worker, guest_worker, NULL, NULL, 2*1024*1024, 0x2d, core);
        if (R_FAILED(rc) && core >= 0) {
            core = -2;
            rc = threadCreate(&worker, guest_worker, NULL, NULL, 2*1024*1024, 0x2d, core);
        }
        fprintf(boot_log,"[THREADS] ui_core=%u guest_core=%d allowed=%llx\n",
                ui_core, core, (unsigned long long)allowed);
        created = R_SUCCEEDED(rc);
        if (created) { rc = threadStart(&worker); started = R_SUCCEEDED(rc); }
    }
    if (R_SUCCEEDED(threadCreate(&input, input_worker, &pad, NULL, 64*1024, 0x2b, -2))) {
        input_started = R_SUCCEEDED(threadStart(&input));
        if (!input_started) threadClose(&input);
    }
    if (boot_log) { fprintf(boot_log,"[INPUT] dedicated_sampler=%d\n",input_started); fflush(boot_log); }
    unsigned frame = 0, displayed = 0;
    bool force_present = true;
    Framebuffer surface = {0};
    bool viewing = false, offered = false, exiting = false, stop_reported = false;
    Result display_error = 0;
    while (appletMainLoop()) {
        if (!input_started) poll_input(&pad);
#ifdef NGB_DIRECT3D
        if (started && !exiting && viewing) sample_guest_thread(&worker);
        static bool profiles_saved;
        if (!profiles_saved && atomic_load(&completed_windows) == PROFILE_WINDOWS) {
            write_guest_samples(PROFILE_WINDOWS);
            profiles_saved = true;
        }
#endif
        unsigned action = atomic_exchange(&commands, 0);
        if (!stop_reported && atomic_load(&finished) &&
            (boot_status == NGB_BOOT_UNSUPPORTED || boot_status == NGB_BOOT_ERROR)) {
            stop_reported = true;
            offered = true;
            if (viewing) action |= SHOW_DETAILS;
        }
        if (viewing && (action & SHOW_DETAILS)) {
            atomic_store(&game_view, false);
            framebufferClose(&surface); consoleInit(NULL); viewing = false; frame = 0;
            if (boot_log) { fputs("[DISPLAY] diagnostics opened\n",boot_log); fflush(boot_log); }
        } else if (!viewing && ngb_scanout_ready() && (!offered || (action & SHOW_GAME))) {
            offered = true;
            consoleExit(NULL);
            display_error = framebufferCreate(&surface,nwindowGetDefault(),1280,720,PIXEL_FORMAT_RGBA_8888,2);
            if (R_SUCCEEDED(display_error)) {
                display_error = framebufferMakeLinear(&surface);
                if (R_FAILED(display_error)) framebufferClose(&surface);
            }
            viewing = R_SUCCEEDED(display_error);
            atomic_store(&game_view, viewing);
            force_present = true;
            if (!viewing) {
                fprintf(boot_log,"[DISPLAY] framebuffer setup failed rc=%08x\n",display_error);
                fflush(boot_log);
                consoleInit(NULL);
                frame=0;
            }
        }
        if (action & EXIT_GAME) {
            ngb_request_stop();
            exiting = true;
        }
        if (exiting && (!started || atomic_load(&finished))) break;
        if (viewing) {
            unsigned next = ngb_scanout_generation();
            if (!force_present && displayed == next) {
                svcSleepThread(4000000);
                continue;
            }
            displayed = next;
            force_present = false;
            u32 stride=0;
            u32 *dst=framebufferBegin(&surface,&stride);
            ngb_scanout_blit(dst,stride/4,1280,720);
            framebufferEnd(&surface);
            ngb_scanout_displayed();
            ngb_movie_displayed();
            static bool logged=false;
            if (!logged && dst && stride>=1280*4) {
                fprintf(boot_log,"[DISPLAY] first guest scanout queued to Switch framebuffer\n");
                fflush(boot_log); logged=true;
            }
            continue;
        }
        if (frame++ % 15 == 0) {
            consoleClear();
#ifdef NGB_RIGID_CLIP
            printf("NGB SWITCH - GAME STARTUP 0.51.0-rc1\n\n");
#elif defined(NGB_REGISTER_PACKAGE)
            printf("NGB SWITCH - GAME STARTUP 0.50.0-rc1\n\n");
#else
            printf("NGB SWITCH - GAME STARTUP 0.49.0\n\n");
#endif
            printf("This build executes the recompiled XBE startup.\n");
            printf("Story mode requires a complete extracted game disc.\n\n");
            if (!started) printf("START FAILED: rc=%08x log=%s\n", rc, boot_log ? "open" : "failed");
            else if (!atomic_load(&finished)) printf("Running game startup...\n");
            else {
                printf("STOPPED (status %d)\n%s\n", boot_status, startup_error ? startup_error : ngb_boot_reason());
                printf("Unsupported services stop here instead of faking success.\n");
            }
            if (ngb_scanout_ready()) printf("Game screen: 720x480. A: view / hold MINUS + tap B: details / PLUS: Start\n");
            if (R_FAILED(display_error)) printf("Display error: %08x\n", display_error);
            printf("\nLog: /switch/ngb-runtime/logs/boot.log\n");
            printf("PLUS: cancel / exit to hbmenu\n");
        }
        consoleUpdate(NULL);
    }
    atomic_store(&input_stop, true);
    if (input_started) { threadWaitForExit(&input); threadClose(&input); }
    ngb_request_stop();
    if (started) threadWaitForExit(&worker);
    if (created) threadClose(&worker);
#ifdef NGB_DIRECT3D
    write_guest_samples(PROFILE_WINDOWS);
#endif
    if (boot_log) fclose(boot_log);
    romfsExit();
    if (viewing) framebufferClose(&surface); else consoleExit(NULL);
    return 0;
}
#else
int main(int argc, char **argv)
{
    if (argc != 3) { fprintf(stderr, "usage: %s default.xbe scratch-data-directory\n", argv[0]); return 2; }
    char disc_root[1024];
    if (strlen(argv[1]) >= sizeof(disc_root)) return 2;
    strcpy(disc_root, argv[1]);
    char *slash = strrchr(disc_root, '/');
    if (slash) { if (slash == disc_root) slash[1] = 0; else *slash = 0; }
    else strcpy(disc_root, ".");
    if (ngb_files_init(disc_root, argv[2])) { fprintf(stderr, "virtual disk initialization failed\n"); return 2; }
    ngb_ohci_pad_present(1); /* Headless fixture: one attached controller. */
    return ngb_boot(argv[1], stdout);
}
#endif
