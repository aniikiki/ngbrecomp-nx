// Guest records are single writer. UI publishes immutable records with a
// release store; never block either thread or write the SD during a sample.
#include "mission_perf.h"
#include "diagnostics_flag.h"
#include "scanout.h"
enum { MP_LIMIT = 2400 };
typedef struct {
    unsigned state, n[MP_COUNT], px[2], pad_bits, cpu_error, published, displayed;
    uint64_t ns[3], cpu[3], detail[5], entries, polls, switches;
} MissionRow;
typedef struct { unsigned id; uint64_t acquire, blit, end; } MissionDisplay;
static MissionRow mp_rows[MP_LIMIT];
static MissionDisplay mp_ui[MP_LIMIT];
static unsigned mp_n, mp_written, mp_ui_written;
static atomic_uint mp_ui_n, mp_ui_id, mp_exited;
int ngb_mission_enabled;
unsigned ngb_mission_guest_id;
static unsigned mp_pub,mp_displayed;
static uint64_t mp_last, mp_cpu, mp_entries, mp_polls, mp_switches;

void ngb_mission_count(unsigned kind,uint64_t ns,unsigned amount) {
    MissionRow *r=&mp_rows[ngb_mission_guest_id-1];
    ++r->n[kind];
    if(kind==MP_FINISH || kind==MP_POST_FINISH)r->detail[3+kind-MP_FINISH]+=ns;
    if(kind==MP_PAD) r->pad_bits|=amount;
    if(kind<=MP_UPLOAD) r->detail[kind]+=ns;
    if(kind==MP_READ || kind==MP_UPLOAD) r->px[kind-MP_READ]+=amount;
}
void ngb_mission_stage(unsigned stage,unsigned state) {
    if(!ngb_mission_enabled || (!stage && mp_n==MP_LIMIT)) return;
    if(stage && !ngb_mission_guest_id)return;
    uint64_t now=ngb_elapsed_ns(), e,p,s,k;
    u64 cpu=0;
    Result rc=thread_ticks(threadGetSelf()->handle,&cpu);
    if(!stage){
        ngb_mission_guest_id=mp_n+1;
        mp_rows[mp_n].state=state;
        mp_pub=ngb_scanout_generation();mp_displayed=ngb_scanout_display_count();
        ngb_profile_work_counts(&mp_entries,&mp_polls,&mp_switches,&k);
        atomic_store(&mp_ui_id,mp_n+1);
    }
    MissionRow *r=&mp_rows[mp_n]; r->cpu_error|=rc;
    if(stage){
        r->ns[stage-1]=now-mp_last;
        if(!r->cpu_error)r->cpu[stage-1]=cpu-mp_cpu;
    }
    mp_last=now;mp_cpu=cpu;
    if(stage==3){
        ngb_profile_work_counts(&e,&p,&s,&k);
        r->published=ngb_scanout_generation()-mp_pub;r->displayed=ngb_scanout_display_count()-mp_displayed;
        r->entries=e-mp_entries;r->polls=p-mp_polls;r->switches=s-mp_switches;
        ngb_mission_guest_id=0;atomic_store(&mp_ui_id,0);++mp_n;
    }
}
static void mp_display(unsigned id,uint64_t a,uint64_t b,uint64_t c,uint64_t d){
    unsigned n=atomic_load_explicit(&mp_ui_n,memory_order_relaxed);
    if(n==MP_LIMIT)return;
    mp_ui[n]=(MissionDisplay){id,b-a,c-b,d-c};
    atomic_store_explicit(&mp_ui_n,n+1,memory_order_release);
}
void ngb_mission_dump(void){
    if(!ngb_mission_enabled)return;
    atomic_store(&mp_exited,1);
    unsigned u=atomic_load_explicit(&mp_ui_n,memory_order_acquire);
    if(mp_written==mp_n && mp_ui_written==u)return;
    static int opened;
    FILE *f=fopen(NGB_LOG_DIR "/menu-perf.csv",opened?"a":"w");
    if(!f)return;
    if(!opened){
        fputs("# M: iteration,state,update_us,draw_us,wait_call_us,update_cpu_us,draw_cpu_us,wait_cpu_us,cpu_rc,entries,polls,fiber_switches,strips,strip_us,gl_draws,gl_reads,read_us,read_px,fb_uploads,upload_us,upload_px,vk_draws,vk_presents,guest_flips,thumb_hit,thumb_miss,pad_reports,pad_bits,published,displayed,split_reads,finish_us,post_finish_read_us\n# D: iteration_at_acquire,acquire_us,blit_overlay_us,end_us\n",f);
        opened=1;
    }
    for(;mp_written<mp_n;mp_written++){
        MissionRow *r=&mp_rows[mp_written];
        fprintf(f,"M,%u,%u",mp_written+1,r->state);
        for(unsigned j=0;j<3;j++)fprintf(f,",%llu",(unsigned long long)(r->ns[j]/1000));
        for(unsigned j=0;j<3;j++)fprintf(f,",%llu",(unsigned long long)armTicksToNs(r->cpu[j])/1000);
        fprintf(f,",%u,%llu,%llu,%llu,%u,%llu,%u,%u,%llu,%u,%u,%llu,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%llu,%llu\n",r->cpu_error,
          (unsigned long long)r->entries,(unsigned long long)r->polls,(unsigned long long)r->switches,
          r->n[MP_STRIP],(unsigned long long)(r->detail[0]/1000),r->n[MP_GL_DRAW],r->n[MP_READ],(unsigned long long)(r->detail[1]/1000),r->px[0],
          r->n[MP_UPLOAD],(unsigned long long)(r->detail[2]/1000),r->px[1],r->n[MP_VK_DRAW],r->n[MP_VK_PRESENT],r->n[MP_FLIP],r->n[MP_THUMB_HIT],r->n[MP_THUMB_MISS],r->n[MP_PAD],r->pad_bits,r->published,r->displayed,r->n[MP_FINISH],(unsigned long long)(r->detail[3]/1000),(unsigned long long)(r->detail[4]/1000));
    }
    for(;mp_ui_written<u;mp_ui_written++){
        MissionDisplay *r=&mp_ui[mp_ui_written];
        fprintf(f,"D,%u,%llu,%llu,%llu\n",r->id,(unsigned long long)(r->acquire/1000),(unsigned long long)(r->blit/1000),(unsigned long long)(r->end/1000));
    }
    fclose(f);
}
