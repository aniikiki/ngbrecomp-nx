/* A dedicated consumer owns the file. One producer per ring: guest, renderer,
 * UI. Producers never wait for the SD card or overwrite unread entries. */
#include "combat_perf.h"
#include <stdatomic.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
enum { CP_CAP=512, CP_COLS=32 };
typedef struct {unsigned kind,n;uint64_t v[CP_COLS];} CombatRow;
static struct {atomic_uint head,tail,lost;CombatRow rows[CP_CAP];} cp_ring[3];
int ngb_combat_enabled;
static atomic_int cp_active;
static atomic_uint_fast64_t cp_wait_ns;
void ngb_combat_wait(int active){
 static _Thread_local uint64_t start;
 if(active){start=ngb_combat_active()?ngb_elapsed_ns():0;}
 else if(start){atomic_fetch_add(&cp_wait_ns,ngb_elapsed_ns()-start);start=0;}
}
uint64_t ngb_combat_wait_us(void){return atomic_load(&cp_wait_ns)/1000;}
static FILE *cp_file;
static char cp_file_buffer[64*1024];
static uint64_t cp_last_flush;
int ngb_combat_active(void){return atomic_load_explicit(&cp_active,memory_order_relaxed);}
uint64_t ngb_combat_cpu_us(void){
#ifdef __SWITCH__
 Thread *self=threadGetSelf();u64 tick;return self && R_SUCCEEDED(thread_ticks(self->handle,&tick))?armTicksToNs(tick)/1000:0;
#else
 struct timespec t;return clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t)?0:(uint64_t)t.tv_sec*1000000+t.tv_nsec/1000;
#endif
}
void ngb_combat_row(int kind,const uint64_t *v,unsigned n){
 unsigned i=(kind=='G'||kind=='N'||kind=='V'||kind=='T')?0:(kind=='R'||kind=='Q'||kind=='B'?1:2),h=atomic_load_explicit(&cp_ring[i].head,memory_order_relaxed);
 if(n>CP_COLS || h-atomic_load_explicit(&cp_ring[i].tail,memory_order_acquire)>=CP_CAP){
  atomic_fetch_add(&cp_ring[i].lost,1);return;}
 CombatRow *r=&cp_ring[i].rows[h%CP_CAP];r->kind=kind;r->n=n;memcpy(r->v,v,n*sizeof(*v));
 atomic_store_explicit(&cp_ring[i].head,h+1,memory_order_release);
}
void ngb_combat_guest(unsigned frame,unsigned id,unsigned mode,unsigned diff,unsigned hp,unsigned maxhp,
 unsigned display,uint64_t ops,uint64_t bytes,uint64_t io){
 // The automatic title battle uses mission 255 / mode 0. Include its live
 // frames so first-draw stalls can be measured even after compilation is warm.
 int on=(id==23 && mode==3) || (id==255 && mode==0 && maxhp>0);
 int prev=atomic_exchange_explicit(&cp_active,on,memory_order_relaxed);
 if(on || prev){uint64_t v[]={frame,ngb_elapsed_ns()/1000,ngb_combat_cpu_us(),id,mode,diff,hp,maxhp,display,ops,bytes,io,on};
 ngb_combat_row('G',v,sizeof v/sizeof *v);}
}
static int combat_open(const char *path){
 cp_file=fopen(path,"a+");if(!cp_file)return 0;
 setvbuf(cp_file,cp_file_buffer,_IOFBF,sizeof cp_file_buffer);
 fprintf(cp_file,"#SESSION,0.56.25,clock_us=monotonic,cpu_us=thread_total_or_zero\n"
 "#G,guest_flip,time_us,cpu_us,mission_id,mode,difficulty,hp,max_hp,display_total,io_ops_total,io_bytes_total,io_us_total,active\n"
 "#R,present,time_us,cpu_us,draw_calls,drawn,descriptor_requests,writes,geometry_bytes,reused_bytes,shaders,pipelines,compile_us,texture_uploads,texture_us,max_tex_us,max_tex_w,max_tex_h,max_tex_fmt,queue_us,fence_us,publish_us,present_us,rt_changes,small_rt_draws,blend_draws,indices,draw_samples,sampled_draw_wall_us,sampled_draw_cpu_us,gpu_query_slots,guest_wait_us_total\n"
 "#Q,submit_frame,read_time_us,gpu_us,valid\n"
 "#D,generation,time_us,acquire_us,blit_overlay_us,submit_us\n"
 "#P,time_us,renderer,pc_offset,lr_offset,pause_cost_us,rc\n"
 "#C,time_us,cpu_hz,gpu_hz,emc_hz,cpu_rc,gpu_rc,emc_rc\n"
 "#F,time_us,write_us,rows\n"
#ifdef NGB_NATIVE_DIAG
 "#N,native_frame,time_us,cpu_us,frame_wall_us,frame_cpu_us,profiled,draws,state_calls,shader_calls,resource_calls,draw_calls,helper_calls,other_calls,flush_calls,inline_words,frame_wait_us,fence_wait_us,resource_wait_us,readback_wait_us,vblank_active_us,pace_active_us,present_us,callback_us,frame_wait_calls,resource_wait_calls,readback_calls\n"
 "#V,native_frame,entry_us,entry_cpu_us,interval,periods,previous_blank,entry_blank,target_blank,retargeted,deadline_us,wait_start_us,wait_wall_us,wait_cpu_us,present_start_us,present_wall_us,swap_wall_us,swap_cpu_us,exit_blank,draws\n"
 "#T,native_frame,time_us,state_ns,shader_ns,resource_ns,draw_ns,helper_ns,other_ns,inline_ns,deferred_ns,record_ns,poll_ns,present_ns,callback_ns,frame_wait_ns,fence_wait_ns,resource_wait_ns,readback_wait_ns,vblank_wait_ns,pace_ns\n"
 "#B,present,time_us,requests,targets,staging_bytes,wall_us,cpu_us,submit_us,max_us\n"
#endif
 );fflush(cp_file);
 if(ferror(cp_file)){fclose(cp_file);cp_file=NULL;return 0;}
 return 1;
}
static void combat_flush(int force){
 if(!cp_file)return;
 if(!force){
  int pending=0;
  for(unsigned i=0;i<3;++i)
   pending|=atomic_load_explicit(&cp_ring[i].head,memory_order_acquire)!=atomic_load(&cp_ring[i].tail) || atomic_load(&cp_ring[i].lost)!=0;
  if(!pending)return;
 }
 uint64_t now=ngb_elapsed_ns();if(!force && now-cp_last_flush<1000000000ull)return;
 cp_last_flush=now;
 int any=0;unsigned rows=0;
 for(unsigned i=0;i<3;i++){unsigned t=atomic_load(&cp_ring[i].tail),h=atomic_load_explicit(&cp_ring[i].head,memory_order_acquire);
 while(t!=h){CombatRow *r=&cp_ring[i].rows[t%CP_CAP];fputc(r->kind,cp_file);for(unsigned j=0;j<r->n;j++)fprintf(cp_file,",%" PRIu64,r->v[j]);fputc('\n',cp_file);++t;++rows;any=1;}
 atomic_store_explicit(&cp_ring[i].tail,t,memory_order_release);unsigned lost=atomic_exchange(&cp_ring[i].lost,0);
 if(lost){fprintf(cp_file,"#LOST,%u,%u\n",i,lost);any=1;}}
 if(any){
  fflush(cp_file);
  fprintf(cp_file,"F,%" PRIu64 ",%" PRIu64 ",%u\n",now/1000,(ngb_elapsed_ns()-now)/1000,rows);
 }
}

#ifdef __SWITCH__
static Thread cp_writer;
static atomic_bool cp_writer_stop;
static bool cp_writer_started;
static void combat_write_worker(void *unused){
 (void)unused;
 while(!atomic_load_explicit(&cp_writer_stop,memory_order_acquire)){
  combat_flush(0);svcSleepThread(10000000);
 }
 combat_flush(1);
}
static int combat_start_writer(void){
 Result rc=threadCreate(&cp_writer,combat_write_worker,NULL,NULL,128*1024,0x31,-2);
 if(R_SUCCEEDED(rc)){
  rc=threadStart(&cp_writer);
  if(R_SUCCEEDED(rc)){cp_writer_started=true;return 1;}
  threadClose(&cp_writer);
 }
 fprintf(cp_file,"#LOGGER_ERROR,start,%08x\n",rc);
 fclose(cp_file);cp_file=NULL;return 0;
}
static void combat_close(void){
 if(cp_writer_started){
  atomic_store_explicit(&cp_writer_stop,true,memory_order_release);
  threadWaitForExit(&cp_writer);threadClose(&cp_writer);cp_writer_started=false;
 }
 if(cp_file){fclose(cp_file);cp_file=NULL;}
}
#endif
