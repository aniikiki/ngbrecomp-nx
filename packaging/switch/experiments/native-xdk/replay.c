/* Headless replay services. All saves and captures are supplied in a scratch directory. */
#include "native-runtime.inc"
#include "direct/output.h"
#include "audio_output.inc"
#include "scanout.h"
#ifdef NGB_NATIVE_DIAG
#include <pthread.h>
#include "native_combat_perf.inc"
static atomic_int replay_log_done;
static void *replay_log_thread(void *unused) {
    (void)unused;
    const struct timespec pause={0,10000000};
    while (!atomic_load(&replay_log_done)) { combat_flush(0); nanosleep(&pause,NULL); }
    combat_flush(1); return NULL;
}
#endif

static FILE *replay_csv;
static FILE *material_csv;
static FILE *mesh_csv;
static FILE *effects_csv;
static FILE *load_csv;
static const char *replay_input_path;
static unsigned replay_draws;
static uint64_t replay_cpu_previous;
static unsigned replay_battle_frames, replay_story_frames, replay_damaged, replay_finished;
static unsigned replay_game_frames;
static unsigned replay_frame_limit, replay_trace_start;
static unsigned replay_mission_rows = 5, replay_mission_column;
static int replay_specific_mission, replay_trace_battle;
#ifdef NGB_NATIVE_CONTRACT_TEST
unsigned ngb_native_test_callback_hits;
void __real_ngb_graphics_callback(uint32_t, uint32_t);
void __wrap_ngb_graphics_callback(uint32_t routine, uint32_t argument) {
    if (routine == 0xfffffff0u) {
        if (argument != 0x12345678) ngb_stop("callback argument changed", argument);
        ++ngb_native_test_callback_hits;
    } else __real_ngb_graphics_callback(routine, argument);
}
#endif
int __real_d3d_hook(int);
int __wrap_d3d_hook(int fn)
{
    uint64_t start=now_ns();
    int result=__real_d3d_hook(fn);
#ifdef NGB_NATIVE_CONTRACT_TEST
    if (fn == 86) {
        extern void ngb_d3d_native_test(void);
        ngb_d3d_native_test(); replay_finished = 1;
        ngb_stop("native contract test completed", 0);
    }
#endif
    uint64_t elapsed=now_ns()-start;
    if(elapsed>100000000) fprintf(stderr,"[API-WAIT] fn=%d ns=%llu\n",fn,(unsigned long long)elapsed);
    if ((fn>=69 && fn<=72) || fn==84) ++replay_draws;
    if (fn==85) {
        if (load_csv) fprintf(load_csv,"%u,%u,%u,%u,%.3f,%.3f,%d,%u,%u,%u\n",
            replay_game_frames + 1, ram[0x589758], ram[0x58975a], MEM16(0xdb9c6e),
            MEMF(0xd21698), MEMF(0xd2169c), (int32_t)MEM32(0x8cda5c),
            MEM32(0x8c5734), MEM8(0x8ce038), MEM32(0xd21734));
        uint64_t material[4];
        ngb_d3d_material_stats(material);
        uint64_t mesh[8]; ngb_d3d_mesh_stats(mesh);
        mesh[2] = material[2]; // Original and native paths count at the same mesh boundary.
        replay_draws = (unsigned)mesh[7]; // Native model draws bypass the old API hooks.
        if (mesh_csv) fprintf(mesh_csv,"%llu,%llu,%llu,%llu,%llu,%llu,%llu,%llu\n",
            (unsigned long long)mesh[0], (unsigned long long)mesh[1], (unsigned long long)mesh[2],
            (unsigned long long)mesh[3], (unsigned long long)mesh[4], (unsigned long long)mesh[5],
            (unsigned long long)mesh[6], (unsigned long long)mesh[7]);
        if (material_csv) fprintf(material_csv,"%llu,%llu,%llu,%llu\n",
            (unsigned long long)material[0],(unsigned long long)material[1],
            (unsigned long long)material[2],(unsigned long long)material[3]);
        ++replay_game_frames;
        if (replay_trace_battle && ram[0x58975a] == 3 && MEM16(0x58a564) && replay_draws >= 250) {
            extern volatile int ngb_trace_request;
            ngb_trace_request = 1;
            replay_trace_battle = 0;
        }
        if (replay_trace_start && replay_game_frames >= replay_trace_start) {
            extern volatile int ngb_trace_request;
            ngb_trace_request = 1;
            replay_trace_start = 0;
        }
        if(effects_csv && ram[0x589758]==23 && MEM16(0x58a564)==2400)
            fprintf(effects_csv,"%u,%llu,%u,%u,%u,%u,%u,%u\n",replay_game_frames,
                (unsigned long long)(ngb_elapsed_ns()/1000),MEM16(0x4968b0),MEM16(0x5895e2),
                MEM16(0x5895e4),MEM16(0x5895e6),MEM16(0x5895e8),replay_draws);
        if (getenv("NGB_REPLAY_EFFECTS") && ram[0x589758]==23 && MEM16(0x58a564)==2400) {
            // Same segment repair and checksum flags as src/cheats.c, confined
            // to the scratch collector. Filling the HUD total alone is not enough.
            int wrote=0;
            if (MEM16(0x58a566) && MEM16(0x58a566)<2400) replay_damaged=1;
            for(unsigned i=0;i<8;++i) {
                uint16_t most=MEM16(0x58a524+2*i);
                if(most && most!=0xffff && MEM16(0x58a534+2*i)!=most) {
                    MEM16(0x58a534+2*i)=most;wrote=1;
                }
            }
            if(MEM16(0x58a566)!=2400){MEM16(0x58a566)=2400;wrote=1;}
            if(wrote)for(unsigned i=0;i<24;++i)MEM8(0x7f1a94+i)=1;
        }
        if (getenv("NGB_REPLAY_NEWGAME") && MEM16(0x58a564) && replay_draws >= 250) ++replay_story_frames;
        if ((replay_specific_mission ? ram[0x58975a] == 3 && MEM16(0x58a564) != 0 :
             ram[0x589758] == 23 && MEM16(0x58a564) == 2400) && replay_draws >= 250) {
            ++replay_battle_frames;
            if (MEM16(0x58a566) < 2400 && MEM16(0x58a566)) replay_damaged = 1;
        }
        struct timespec cpu; clock_gettime(CLOCK_THREAD_CPUTIME_ID,&cpu);
        uint64_t ns=(uint64_t)cpu.tv_sec*1000000000+cpu.tv_nsec;
        if(replay_csv) fprintf(replay_csv,"%llu,%u,%u,%u,%u,%u,%llu\n",(unsigned long long)(ngb_elapsed_ns()/1000),
            ram[0x589758],ram[0x58975a],MEM16(0x58a566),MEM16(0x58a564),replay_draws,
            (unsigned long long)(replay_cpu_previous?ns-replay_cpu_previous:0));
        replay_cpu_previous=ns;replay_draws=0;
    }
    return result;
}

static uint64_t replay_start;
static unsigned replay_key, replay_shots;
static unsigned replay_limit = 120;
static unsigned replay_second;
static unsigned replay_buttons;
static uint64_t replay_menu_ms;
static unsigned replay_menu_frame;
static unsigned replay_mission_key;
static unsigned mission_keys[40][2], mission_key_count;
static void mission_tap(unsigned at, unsigned buttons) {
    mission_keys[mission_key_count][0] = at;
    mission_keys[mission_key_count++][1] = buttons;
    mission_keys[mission_key_count][0] = at + (replay_specific_mission ? 67 : 180);
    mission_keys[mission_key_count++][1] = 0;
}
void replay_unlock(uint32_t menu)
{
    if (!getenv("NGB_REPLAY_ALMA") && !replay_input_path) return;
    MEM8(MEM32(menu)+20)=MEM8(MEM32(menu)+21)=1;
    for(unsigned i=0;i<100;i++){MEM8(0xdb95ac+i)|=1;MEM8(0xdb9610+i)=4;}
}
static const unsigned replay_keys[][2] = {
    {1000,16},{1120,0},{7000,16},{7120,0},{14000,16},{14120,0},
};
void __real_ngb_poll_due(uint64_t);
void __wrap_ngb_poll_due(uint64_t ticket)
{
    __real_ngb_poll_due(ticket);
    if (ticket & 255) return;
    uint64_t now = ngb_elapsed_ns();
    if (!replay_start) replay_start = now;
    unsigned ms = (now - replay_start) / 1000000;
    if (ms / 1000 > replay_second) {
        replay_second = ms / 1000;
        fprintf(stderr,"[REPLAY] sec=%u va=%08x menu=%u mission=%u mode=%u hp=%u/%u frames=%u\n",
                replay_second,current_va,menu_cursor,ram[0x589758],ram[0x58975a],MEM16(0x58a566),MEM16(0x58a564),replay_shots);
    }
    if (replay_input_path) {
        // Test-only live controller schedule; an isolated replay can visit a
        // reported mission without adding another hard-coded menu sequence.
        static unsigned next_read;
        if (ms >= next_read) {
            next_read = ms + 100;
            FILE *input = fopen(replay_input_path, "r");
            unsigned at, buttons = 0, b;
            int x = 0, y = 0, sx, sy;
            if (input) {
                while (fscanf(input, "%u %u %d %d", &at, &b, &sx, &sy) == 4)
                    if (at <= ms) { buttons = b; x = sx; y = sy; }
                fclose(input);
            }
            ngb_ohci_pad_sample(buttons, x, y, 0, 0);
        }
    }
    if (!replay_input_path && !getenv("NGB_REPLAY_ATTRACT") && replay_key < sizeof replay_keys / sizeof *replay_keys && ms >= replay_keys[replay_key][0]) {
        ngb_ohci_pad_sample(replay_keys[replay_key][1],0,0,0,0);
        fprintf(stderr,"[REPLAY] ms=%u key=%u menu=%u\n",ms,replay_keys[replay_key][1],menu_cursor);
        ++replay_key;
    }
    if (!replay_input_path && !getenv("NGB_REPLAY_ATTRACT") && ms > 17000 && menu_cursor == UINT32_MAX) {
        unsigned buttons = ms % 1500 < 180 ? 16 : 0;
        if (buttons != replay_buttons) { ngb_ohci_pad_sample(buttons,0,0,0,0); replay_buttons=buttons; }
    }
    if (!replay_input_path && menu_cursor != UINT32_MAX && (getenv("NGB_REPLAY_ALMA") || getenv("NGB_REPLAY_NEWGAME"))) {
        if (!replay_menu_ms) {
            replay_menu_ms=ms;
            replay_menu_frame=replay_game_frames;
            ngb_ohci_pad_sample(0,0,0,0,0);
        }
        unsigned t=ms-replay_menu_ms;
        // The original menu polls and repeats buttons in game frames. Four
        // flips per tap also select one cell when the software renderer slows.
        if(replay_specific_mission && !getenv("NGB_REPLAY_NEWGAME"))
            t=(replay_game_frames-replay_menu_frame)*1000ull/60;
        if (getenv("NGB_REPLAY_NEWGAME")) {
            unsigned buttons = t >= 3000 && t < 3180 ? 1 : t >= 5600 && t % 1500 < 180 ? 256 : 0;
            if (buttons != replay_buttons) { ngb_ohci_pad_sample(buttons,0,0,0,0); replay_buttons=buttons; }
        } else if(replay_mission_key<mission_key_count && t>=mission_keys[replay_mission_key][0]) {
            ngb_ohci_pad_sample(mission_keys[replay_mission_key][1],0,0,0,0);
            fprintf(stderr,"[MISSION-KEY] t=%u key=%u menu=%u\n",t,mission_keys[replay_mission_key][1],menu_cursor);
            ++replay_mission_key;
        }
        if(t>45000 && (t<110000 || ((getenv("NGB_REPLAY_EFFECTS") || replay_specific_mission) && !replay_battle_frames)) &&
            !(getenv("NGB_REPLAY_EFFECTS") && replay_battle_frames)) {
            unsigned buttons=t%1500<180?256:0;
            if(buttons!=replay_buttons){ngb_ohci_pad_sample(buttons,0,0,0,0);replay_buttons=buttons;}
        }
    }
    if (getenv("NGB_REPLAY_EFFECTS") && replay_battle_frames && ram[0x589758]==23 && ram[0x58975a]==3 && MEM16(0x58a564)==2400) {
        // Collector only: keep this scratch battle alive while exercising the
        // jump + heavy attack, sustained charge/release, and light attacks.
        static unsigned first, last_phase=~0u;
        if (!first) first=replay_game_frames;
        // Game frames, not wall time: software rendering must still hold a
        // charge for the same number of simulation steps as a 60 FPS Switch.
        unsigned t=(replay_game_frames-first)%900, buttons=0, phase=t<360?0:1+(t-360)/180;
        int16_t forward=0;
        if (t<360) buttons=t<300?2048:0;
        else if (t<540) {
            unsigned step=t%60;
            buttons=step<9?256:step>=13 && step<24?2048:0;
            forward=26000;
        } else if (t<720) buttons=t%30<9?1024:0;
        else { buttons=t%60<30?16384:0; forward=20000; }
        ngb_ohci_pad_sample(buttons,0,forward,0,0);
        if(phase!=last_phase) {
            fprintf(stderr,"[EFFECT-INPUT] ms=%u game_frame=%u phase=%u (0=charge-release 1=jump-heavy 2=light 3=guard-move)\n",ms,replay_game_frames,phase);
            last_phase=phase;
        }
    }
    if (ms >= replay_limit * 1000 || (replay_frame_limit && replay_game_frames >= replay_frame_limit)) {
        ngb_d3d_native_report();
        replay_finished = !getenv("NGB_REPLAY_ALMA") || (replay_battle_frames >= 120 && replay_damaged);
        if (getenv("NGB_REPLAY_NEWGAME")) replay_finished = replay_story_frames >= 120;
        if (replay_frame_limit && replay_game_frames < replay_frame_limit) replay_finished = 0;
        fprintf(stderr, "[REPLAY-%s] battle_frames=%u story_frames=%u damage_seen=%u captures=%u\n",
                replay_finished ? "PASS" : "FAIL", replay_battle_frames, replay_story_frames, replay_damaged, replay_shots);
        ngb_stop("native replay time limit", ms);
    }
}
void __real_ngb_scanout_direct(const void *);
void __wrap_ngb_scanout_direct(const void *pixels)
{
    __real_ngb_scanout_direct(pixels);
    unsigned frame = ++replay_shots;
    unsigned every=getenv("NGB_REPLAY_EFFECTS")?30:120;
    if (frame > 30 && frame != 60 && frame % every) return;
    char path[64]; snprintf(path,sizeof path,"frame-%06u.ppm",frame);
    FILE *f = fopen(path,"wb"); if (!f) return;
    fprintf(f,"P6\n720 480\n255\n");
    const uint32_t *p = pixels;
    for (unsigned y=0;y<480;y++) {
        unsigned char row[720*3];
        for (unsigned x=0;x<720;x++) { uint32_t c=p[y*720+x];row[x*3]=c>>16;row[x*3+1]=c>>8;row[x*3+2]=c; }
        fwrite(row,1,sizeof row,f);
    }
    fclose(f);
}

int main(int argc, char **argv)
{
    if (argc != 3) { fprintf(stderr, "usage: replay GAME_DIRECTORY SCRATCH_HDD\n"); return 2; }
    char image[1024];
    if (snprintf(image, sizeof(image), "%s/default.xbe", argv[1]) >= (int)sizeof(image)) return 2;
    if (ngb_files_init(argv[1], argv[2])) return 2;
    const char *limit = getenv("NGB_REPLAY_SECONDS"); if (limit) replay_limit = strtoul(limit,NULL,10);
    const char *frames = getenv("NGB_REPLAY_FRAMES"); if (frames) replay_frame_limit = strtoul(frames,NULL,10);
    const char *trace = getenv("NGB_REPLAY_TRACE_START"); if (trace) replay_trace_start = strtoul(trace,NULL,10);
    replay_input_path = getenv("NGB_REPLAY_INPUT");
    const char *row = getenv("NGB_REPLAY_MISSION_ROW"), *column = getenv("NGB_REPLAY_MISSION_COLUMN");
    replay_specific_mission = row || column;
    if (row) replay_mission_rows = strtoul(row, NULL, 10);
    if (column) replay_mission_column = strtoul(column, NULL, 10);
    if (replay_mission_rows > 9 || replay_mission_column > 4) return 2;
    replay_trace_battle = getenv("NGB_REPLAY_TRACE_BATTLE") != NULL;
    mission_tap(3000, 2); mission_tap(5600, 256);
    unsigned first = replay_specific_mission ? 11000 : 8000;
    unsigned interval = replay_specific_mission ? 2200 : 900;
    for (unsigned i = 0; i < replay_mission_rows; ++i) mission_tap(first + interval * i, 2);
    unsigned next = first + interval * replay_mission_rows;
    for (unsigned i = 0; i < replay_mission_column; ++i) mission_tap(next + interval * i, 8);
    next += interval * replay_mission_column;
    if (next < 15300) next = 15300;
    mission_tap(next, 256); mission_tap(next + 3300, 256); mission_tap(next + 7200, 256);
    if (getenv("NGB_REPLAY_LOAD_TRACE")) {
        load_csv = fopen("load.csv", "w");
        if (load_csv) {
            setvbuf(load_csv, NULL, _IOLBF, 0);
            fprintf(load_csv,"frame,mission,mode,mission_override,cpu_load,gpu_load,quality,shadow_enabled,player_slot,load_flags\n");
        }
    }
    replay_csv=fopen("frames.csv","w");
    material_csv=fopen("material.csv","w");
    mesh_csv=fopen("mesh.csv","w");
    fprintf(mesh_csv,"native_frame,enabled,attempts,batches,submitted,syncs,reused,frame_draws\n");
    fprintf(material_csv,"native_frame,enabled,attempts,batches\n");
    if(replay_csv)fprintf(replay_csv,"time_us,mission,mode,hp,max_hp,draw_apis,cpu_ns\n");
    if(getenv("NGB_REPLAY_EFFECTS")) {
        effects_csv=fopen("effects.csv","w");
        if(effects_csv)fprintf(effects_csv,"game_frame,time_us,action_kind,charge_level,charge_ticks,et_mark,ut_mark,draw_apis\n");
    }
    ngb_ohci_pad_present(1);
#ifdef NGB_NATIVE_DIAG
    pthread_t logger;
    if (combat_requested("alma-perf.flag")) {
        ngb_combat_enabled = combat_open("native-perf.csv");
        if (!ngb_combat_enabled || pthread_create(&logger,NULL,replay_log_thread,NULL)) return 2;
    }
#endif
    int result=ngb_boot(image, stdout);
#ifdef NGB_NATIVE_DIAG
    if (ngb_combat_enabled) {
        atomic_store(&replay_log_done,1); pthread_join(logger,NULL); fclose(cp_file);
    }
#endif
    if(replay_csv)fclose(replay_csv);
    if(effects_csv)fclose(effects_csv);
    if(load_csv)fclose(load_csv);
    return replay_finished ? 0 : result ? result : 1;
}
