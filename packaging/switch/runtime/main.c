#include "runtime.h"
#include "profile.h"
#include "audio_output.h"
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
#include "player_diagnostics.h"
int ngb_diagnostics_enabled;
#include "loading.inc"
#ifdef NGB_PLAYER_BUILD
static atomic_uint commands;
#include "settings_panel.inc"
#endif
static atomic_bool finished;
static int boot_status;
static FILE *boot_log;
static const char *startup_error;
static atomic_bool input_stop, game_view, gameplay_controls;
void ngb_frontend_menu_controls(void) {
    atomic_store(&gameplay_controls,true);
#ifdef NGB_PLAYER_BUILD
    atomic_store(&exit_return_boot,false);
#endif
}
#ifndef NGB_PLAYER_BUILD
static atomic_uint commands;
#endif
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

#ifdef NGB_PLAYER_BUILD
#include "mission_perf.inc"
#ifdef NGB_COMBAT_PERF
#include "combat_perf.inc"
#endif
#endif

void ngb_profile_next_frame(unsigned frame, unsigned draws)
{
    if (frame==1) atomic_store(&gameplay_controls,true);
    if (!ngb_diagnostics_enabled) return;
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

#ifdef NGB_PLAYER_BUILD
// UI-owned buffer; the guest never takes a lock or writes this trace.
static int mp_pc_enabled;
static struct { unsigned id,pc,lr,cost_us,rc; } mp_pc[1024];
static unsigned mp_pc_count,mp_pc_saved;
#ifdef NGB_COMBAT_PERF
/* UI sampler: only query context while paused; release before recording. */
static void combat_pc(Thread *th,unsigned renderer){
    ThreadContext ctx;uint64_t now=ngb_elapsed_ns();uint32_t pc=UINT32_MAX,lr=UINT32_MAX;
    Result rc=threadPause(th);
    if(R_SUCCEEDED(rc)){
        rc=threadDumpContext(&ctx,th);
        if(R_SUCCEEDED(rc)){pc=module_offset(ctx.pc.x);lr=module_offset(ctx.lr);}
        Result resumed=threadResume(th);if(R_FAILED(resumed))rc=resumed;
    }
    uint64_t v[]={now/1000,renderer,pc,lr,(ngb_elapsed_ns()-now)/1000,rc};
    ngb_combat_row('P',v,6);
}
static void combat_render_pc(void *th){combat_pc(th,1);}
static void combat_sample(Thread *guest){
    static uint64_t next,clock_due;static unsigned seq;
    if(!ngb_combat_active())return;
    uint64_t now=ngb_elapsed_ns();
    if(now>=clock_due){
        uint64_t v[7]={now/1000};const PcvModuleId id[]={PcvModuleId_CpuBus,PcvModuleId_GPU,PcvModuleId_EMC};
        Result init=clkrstInitialize();
        for(unsigned i=0;i<3;i++){
            ClkrstSession sess;u32 hz=0;Result rc=init;
            if(R_SUCCEEDED(rc))rc=clkrstOpenSession(&sess,id[i],3);
            if(R_SUCCEEDED(rc)){rc=clkrstGetClockRate(&sess,&hz);clkrstCloseSession(&sess);}
            v[i+1]=hz;v[i+4]=rc;
        }
        if(R_SUCCEEDED(init))clkrstExit();
        ngb_combat_row('C',v,7);clock_due=now+5000000000ull;
    }
    if(now<next || !envIsSyscallHinted(0x32) || !envIsSyscallHinted(0x33))return;
    next=now+(97000000u+((++seq*2654435761u)%43000000u));
    if(seq&1)combat_pc(guest,0);else ngb_direct_visit_worker(combat_render_pc);
}
#endif
static void mission_pc_tick(Thread *guest){
    static uint64_t due;
    static unsigned jitter=0x50a143;
    unsigned id=atomic_load(&mp_ui_id);
    if(!id || mp_pc_count==1024)return;
    uint64_t now=armGetSystemTick();
    if(now<due)return;
    jitter=1664525u*jitter+1013904223u;
    due=now+armNsToTicks(43000000u+(jitter%41000000u));
    ThreadContext ctx;
    Result rc=threadPause(guest);
    unsigned pc=UINT32_MAX,lr=UINT32_MAX;
    if(R_SUCCEEDED(rc)){
        // Recheck after suspension: the iteration may already have ended.
        id=atomic_load(&mp_ui_id);
        rc=threadDumpContext(&ctx,guest);
        if(R_SUCCEEDED(rc)){pc=module_offset(ctx.pc.x);lr=module_offset(ctx.lr);}
        Result resumed=threadResume(guest);
        if(R_FAILED(resumed))rc=resumed;
    }
    if(id || R_FAILED(rc)){
        mp_pc[mp_pc_count++]=(typeof(mp_pc[0])){id,pc,lr,armTicksToNs(armGetSystemTick()-now)/1000,rc};
        if(R_FAILED(rc))mp_pc_enabled=0;
    }
}
static void mission_pc_save(void){
    if(mp_pc_saved==mp_pc_count)return;
    mkdir("sdmc:/switch/ngb-runtime/logs",0777);
    FILE *f=fopen("sdmc:/switch/ngb-runtime/logs/mission-pc.csv",mp_pc_saved?"a":"w");
    if(!f)return;
    if(!mp_pc_saved)fputs("iteration,pc_offset,lr_offset,sample_us,rc\n",f);
    for(;mp_pc_saved<mp_pc_count;mp_pc_saved++){
        const typeof(mp_pc[0])*v=&mp_pc[mp_pc_saved];
        fprintf(f,"%u,%08x,%08x,%u,%08x\n",v->id,v->pc,v->lr,v->cost_us,v->rc);
    }
    fclose(f);
}
#endif

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
    /* Before gameplay starts, passing B through can tear down
     * the guest movie while its decoder thread is running. */
    uint64_t held=padGetButtons(pad);
    if (!game_input || !atomic_load(&gameplay_controls)) held &= ~HidNpadButton_B;
    else if ((held & (HidNpadButton_Minus|HidNpadButton_B))==(HidNpadButton_Minus|HidNpadButton_B))
        held &= ~(HidNpadButton_Minus|HidNpadButton_B);
    if (!game_input && !ngb_movie_owns_input()) held &= ~HidNpadButton_Plus;
#ifdef NGB_PLAYER_BUILD
    if(atomic_load(&exit_return_boot) && game_input && !atomic_load(&gameplay_controls))
        held|=((armGetSystemTick()/(armGetSystemTickFreq()/4))&3)==1?HidNpadButton_Plus:0;
#endif
    uint16_t buttons=0;
    for (unsigned i=0;i<16;i++) if (held&mapped[i]) buttons|=1u<<i;
#ifdef NGB_PLAYER_BUILD
    ngb_switch_sample_quick(buttons);
#endif
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
#ifdef NGB_PLAYER_BUILD
    if (settings_input(pad)) return;
#endif
    bool game = atomic_load(&game_view);
    u64 down = padGetButtonsDown(pad);
    bool stopped = atomic_load(&finished);
    sample_pad(pad, game && !stopped);
    unsigned action = (stopped || (!game && !ngb_movie_owns_input())) && (down & HidNpadButton_Plus) ? EXIT_GAME : 0;
    if (action) atomic_fetch_or(&commands, action);
    if (boot_log && (down & (HidNpadButton_B | HidNpadButton_Plus))) {
        fprintf(boot_log,"[INPUT] Plus=%d B=%d game_view=%d connected=%d stopped=%d uptime_ms=%llu\n",
                !!(down & HidNpadButton_Plus), !!(down & HidNpadButton_B), game, padIsConnected(pad), stopped,
                (unsigned long long)(armTicksToNs(armGetSystemTick()-launch_tick)/1000000));
        if (boot_log) fflush(boot_log);
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
    if (boot_log) fprintf(boot_log,"[DISC] source=%s\n",external);
    if (stat(image,&st) || !S_ISREG(st.st_mode)) {
        startup_error = "Copy the extracted game to /switch/ngb-runtime/disc (default.xbe missing)";

        boot_status=NGB_BOOT_ERROR;
        if (boot_log) fflush(boot_log);
    } else if (ngb_files_init(external, "sdmc:/switch/ngb-runtime/data")) {

        boot_status = NGB_BOOT_ERROR;
        startup_error = "virtual disk initialization failed";
        if (boot_log) fflush(boot_log);
    } else boot_status = ngb_boot(image, boot_log);
    atomic_store(&finished, true);
}

/* Retained build version: 0.51.0-rc1 */
int main(int argc,char **argv)
{
#ifdef NGB_PLAYER_BUILD
    exit_program_path=(argc && argv[0] && *argv[0])?argv[0]:"sdmc:/switch/ngb-runtime/ngb-startup.nro";
    atomic_store(&exit_return_boot,argc>1 && !strcmp(argv[1],"--return-to-title"));
#else
    (void)argc;(void)argv;
#endif
    launch_tick=armGetSystemTick();
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    padUpdate(&pad);
    sample_pad(&pad, false);
    mkdir("sdmc:/switch", 0777);
    mkdir("sdmc:/switch/ngb-runtime", 0777);
#ifdef NGB_PLAYER_BUILD
    prefs_load();launch_aspect=pref(7);launch_thread=pref(30);
    ngb_quick_set_game_dir("sdmc:/switch/ngb-runtime/disc");
    bow_loaded=ngb_crosshair_picture(bow_art,64);
#endif
    struct stat flag;
#if defined(NGB_PLAYER_BUILD) && defined(NGB_DIRECT3D)
#ifdef NGB_COMBAT_PERF
    if(stat("sdmc:/switch/ngb-runtime/alma-perf.flag",&flag)==0 && S_ISREG(flag.st_mode)){
        mkdir("sdmc:/switch/ngb-runtime/logs",0777);
        ngb_combat_enabled=combat_open("sdmc:/switch/ngb-runtime/logs/alma-perf.csv") && combat_start_writer();
    }
#endif
    ngb_mission_enabled = stat("sdmc:/switch/ngb-runtime/mission-perf.flag",&flag)==0 && S_ISREG(flag.st_mode);
    ngb_mission_gl_split = ngb_mission_enabled && stat("sdmc:/switch/ngb-runtime/mission-gl-sync.flag",&flag)==0 && S_ISREG(flag.st_mode);
    mp_pc_enabled = ngb_mission_enabled && stat("sdmc:/switch/ngb-runtime/mission-pc.flag",&flag)==0 && S_ISREG(flag.st_mode);
#endif
    ngb_diagnostics_enabled = stat("sdmc:/switch/ngb-runtime/diagnostics.flag",&flag)==0 && S_ISREG(flag.st_mode);
    if (ngb_diagnostics_enabled) {
        mkdir("sdmc:/switch/ngb-runtime/logs", 0777);
        const char *current_log = "sdmc:/switch/ngb-runtime/logs/boot.log";
        const char *previous_log = "sdmc:/switch/ngb-runtime/logs/boot.previous.log";
        struct stat last;
        if (!stat(current_log,&last) && last.st_size > 0) {
            remove(previous_log);
            rename(current_log,previous_log);
        }
        boot_log = fopen(current_log, "w");
        if (!boot_log) ngb_diagnostics_enabled=0;
    }
#ifdef NGB_DIRECT3D
    if (boot_log) { fprintf(boot_log, "[CONFIG] kickoff_kib=%u\n", NGB_DIRECT_KICKOFF_KIB); fflush(boot_log); }
#endif
    Result rc = romfsInit();
    Framebuffer surface = {0};
    bool surface_open = false, console_open = false;
    if (R_SUCCEEDED(rc)) {
        if (!load_splash()) { startup_error="Loading artwork missing. Replace the game application."; rc=1; }
        else {
            rc=framebufferCreate(&surface,nwindowGetDefault(),1280,720,PIXEL_FORMAT_RGBA_8888,2);
            if (R_SUCCEEDED(rc)) {
                rc=framebufferMakeLinear(&surface);
                if (R_FAILED(rc)) framebufferClose(&surface);
                else { surface_open=true; show_loading(&surface,0); }
            }
        }
    }
    Thread worker, input;
    bool input_started = false;
    int audio_open=R_SUCCEEDED(rc) && ngb_audio_device_open();
    bool created = false, started = false;
    if (R_SUCCEEDED(rc)) {
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
        if (boot_log) fprintf(boot_log,"[THREADS] ui_core=%u guest_core=%d allowed=%llx\n",
                ui_core, core, (unsigned long long)allowed);
        created = R_SUCCEEDED(rc);
        if (created) { rc = threadStart(&worker); started = R_SUCCEEDED(rc); }
    }
    if (R_SUCCEEDED(threadCreate(&input, input_worker, &pad, NULL, 64*1024, 0x2b, -2))) {
        input_started = R_SUCCEEDED(threadStart(&input));
        if (!input_started) threadClose(&input);
    }
    if (boot_log) { fprintf(boot_log,"[INPUT] dedicated_sampler=%d\n",input_started); fflush(boot_log); }
    unsigned displayed = 0, pulse = 0;
    u64 next_pulse = armGetSystemTick();
    bool viewing = false, exiting = false, reported = false;
    while (appletMainLoop()) {
        if (!input_started) poll_input(&pad);
        bool done=atomic_load(&finished);
        bool failed=!started || (done && (boot_status==NGB_BOOT_ERROR || boot_status==NGB_BOOT_UNSUPPORTED));
        if (failed && !reported) {
            reported=true;
            atomic_store(&game_view,false);
            const char *why=startup_error ? startup_error : started ? ngb_boot_reason() : "Unable to start the game";
            mkdir("sdmc:/switch/ngb-runtime/logs",0777);
            FILE *err=fopen("sdmc:/switch/ngb-runtime/logs/error.log","a");
            if (err) { fprintf(err,"[ERROR] %s (rc=%08x)\n",why,rc); fclose(err); }
            if (surface_open) { framebufferClose(&surface); surface_open=false; }
            consoleInit(NULL); console_open=true;
            printf("Ninja Gaiden Black\n\n%s\n\nPress + to return.\n",why);
            consoleUpdate(NULL);
        }
#if defined(NGB_PLAYER_BUILD) && defined(NGB_DIRECT3D)
#ifdef NGB_COMBAT_PERF
        if(ngb_combat_enabled && started && !done && !exiting)combat_sample(&worker);
#endif
        if(started && !done && !exiting && mp_pc_enabled)mission_pc_tick(&worker);
        if(ngb_mission_enabled && atomic_exchange(&mp_exited,0))mission_pc_save();
#endif
        if (atomic_exchange(&commands,0)&EXIT_GAME) { ngb_request_stop(); exiting=true; }
        if (exiting && (!started || done)) break;
        if (done && !failed) break;
#ifdef NGB_PLAYER_BUILD
        static unsigned previous_panel,previous_revision;
        unsigned view=atomic_load(&panel);
        if (view && !failed && !exiting) {
            unsigned changes=atomic_load(&revision);
            if (previous_panel!=view || previous_revision!=changes) {
                if(view&EXIT_PANEL) draw_exit_panel(&surface,view); else draw_settings(&surface,view);
            }
            previous_panel=view;previous_revision=changes;
            svcSleepThread(4000000);
            continue;
        }
        if (previous_panel) {previous_panel=0;displayed=~0u;}
#endif
        if (!failed && ngb_scanout_ready() && (viewing || ngb_scanout_visible())) {
            unsigned next=ngb_scanout_generation();
            if (!viewing || displayed!=next) {
#if defined(NGB_PLAYER_BUILD) && defined(NGB_DIRECT3D)
                unsigned mid=ngb_mission_enabled?atomic_load(&mp_ui_id):0;
                int measure_display=mid!=0;
#ifdef NGB_COMBAT_PERF
                int combat_display=ngb_combat_enabled && ngb_combat_active();
                measure_display|=combat_display;
#endif
                uint64_t ma=measure_display?ngb_elapsed_ns():0;
#endif
                u32 stride; u32 *dst=framebufferBegin(&surface,&stride);
#if defined(NGB_PLAYER_BUILD) && defined(NGB_DIRECT3D)
                uint64_t mb=measure_display?ngb_elapsed_ns():0;
#endif
                ngb_scanout_blit(dst,stride/4,1280,720);
#ifdef NGB_PLAYER_BUILD
                game_overlay(dst,stride/4);
#endif
#if defined(NGB_PLAYER_BUILD) && defined(NGB_DIRECT3D)
                uint64_t mc=measure_display?ngb_elapsed_ns():0;
#endif
                framebufferEnd(&surface);
#if defined(NGB_PLAYER_BUILD) && defined(NGB_DIRECT3D)
#ifdef NGB_COMBAT_PERF
                if(combat_display){uint64_t end=ngb_elapsed_ns();uint64_t v[]={next,end/1000,(mb-ma)/1000,(mc-mb)/1000,(end-mc)/1000};ngb_combat_row('D',v,5);}
#endif
                if(mid)mp_display(mid,ma,mb,mc,ngb_elapsed_ns());
#endif
                ngb_scanout_displayed(); ngb_movie_displayed();
                displayed=next; viewing=true; atomic_store(&game_view,true);
            }
#ifdef NGB_DIRECT3D
            if (ngb_diagnostics_enabled && !exiting) {
                sample_guest_thread(&worker);
                static bool saved;
                if (!saved && atomic_load(&completed_windows)==PROFILE_WINDOWS) {
                    write_guest_samples(PROFILE_WINDOWS);
                    saved=true;
                }
            }
#endif
        } else if (!failed && !viewing && armGetSystemTick()>=next_pulse) {
            show_loading(&surface,++pulse);
            next_pulse=armGetSystemTick()+armGetSystemTickFreq()/4;
        }
        svcSleepThread(4000000);
    }
    atomic_store(&input_stop, true);
    if (input_started) { threadWaitForExit(&input); threadClose(&input); }
    ngb_request_stop();
    if (started) threadWaitForExit(&worker);
#if defined(NGB_PLAYER_BUILD) && defined(NGB_DIRECT3D)
    ngb_mission_dump();
    mission_pc_save();
#endif
    if (created) threadClose(&worker);
    if(audio_open)ngb_audio_device_close();
#ifdef NGB_DIRECT3D
    write_guest_samples(PROFILE_WINDOWS);
#endif
#ifdef NGB_COMBAT_PERF
    combat_close();
#endif
    if (boot_log) fclose(boot_log);
    romfsExit();
    if (surface_open) framebufferClose(&surface);
    if (console_open) consoleExit(NULL);
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
