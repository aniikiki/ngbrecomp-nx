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
static unsigned replay_draws;
static uint64_t replay_cpu_previous;
static unsigned replay_battle_frames, replay_story_frames, replay_damaged, replay_finished;
static unsigned replay_game_frames;
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
        if (ram[0x589758] == 23 && MEM16(0x58a564) == 2400 && replay_draws >= 250) {
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
static unsigned replay_mission_key;
static const unsigned mission_keys[][2] = {
    {3000,2},{3180,0},{5600,256},{5780,0},{8000,2},{8180,0},{8900,2},{9080,0},
    {9800,2},{9980,0},{10700,2},{10880,0},{11600,2},{11780,0},
    {15300,256},{15480,0},{18600,256},{18780,0},{22500,256},{22680,0}
};
void replay_unlock(uint32_t menu)
{
    if (!getenv("NGB_REPLAY_ALMA")) return;
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
    if (!getenv("NGB_REPLAY_ATTRACT") && replay_key < sizeof replay_keys / sizeof *replay_keys && ms >= replay_keys[replay_key][0]) {
        ngb_ohci_pad_sample(replay_keys[replay_key][1],0,0,0,0);
        fprintf(stderr,"[REPLAY] ms=%u key=%u menu=%u\n",ms,replay_keys[replay_key][1],menu_cursor);
        ++replay_key;
    }
    if (!getenv("NGB_REPLAY_ATTRACT") && ms > 17000 && menu_cursor == UINT32_MAX) {
        unsigned buttons = ms % 1500 < 180 ? 16 : 0;
        if (buttons != replay_buttons) { ngb_ohci_pad_sample(buttons,0,0,0,0); replay_buttons=buttons; }
    }
    if (menu_cursor != UINT32_MAX && (getenv("NGB_REPLAY_ALMA") || getenv("NGB_REPLAY_NEWGAME"))) {
        if (!replay_menu_ms) { replay_menu_ms=ms;ngb_ohci_pad_sample(0,0,0,0,0); }
        unsigned t=ms-replay_menu_ms;
        if (getenv("NGB_REPLAY_NEWGAME")) {
            unsigned buttons = t >= 3000 && t < 3180 ? 1 : t >= 5600 && t % 1500 < 180 ? 256 : 0;
            if (buttons != replay_buttons) { ngb_ohci_pad_sample(buttons,0,0,0,0); replay_buttons=buttons; }
        } else if(replay_mission_key<sizeof mission_keys/sizeof *mission_keys && t>=mission_keys[replay_mission_key][0]) {
            ngb_ohci_pad_sample(mission_keys[replay_mission_key][1],0,0,0,0);
            fprintf(stderr,"[MISSION-KEY] t=%u key=%u menu=%u\n",t,mission_keys[replay_mission_key][1],menu_cursor);
            ++replay_mission_key;
        }
        if(t>45000 && (t<110000 || (getenv("NGB_REPLAY_EFFECTS") && !replay_battle_frames)) &&
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
    if (ms >= replay_limit * 1000) {
        ngb_d3d_native_report();
        replay_finished = !getenv("NGB_REPLAY_ALMA") || (replay_battle_frames >= 120 && replay_damaged);
        if (getenv("NGB_REPLAY_NEWGAME")) replay_finished = replay_story_frames >= 120;
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
    ngb_combat_enabled = combat_open("native-perf.csv");
    if (!ngb_combat_enabled || pthread_create(&logger,NULL,replay_log_thread,NULL)) return 2;
#endif
    int result=ngb_boot(image, stdout);
#ifdef NGB_NATIVE_DIAG
    atomic_store(&replay_log_done,1); pthread_join(logger,NULL); fclose(cp_file);
#endif
    if(replay_csv)fclose(replay_csv);
    if(effects_csv)fclose(effects_csv);
    return replay_finished ? 0 : result ? result : 1;
}
