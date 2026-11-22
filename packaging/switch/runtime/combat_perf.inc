/* A dedicated consumer owns the file. One producer per ring: guest, renderer,
 * UI. Producers never wait for the SD card or overwrite unread entries. */
#include "combat_perf.h"
#include <stdatomic.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
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
 unsigned i=(kind=='G'||kind=='I'||kind=='J'||kind=='M'||kind=='U'||kind=='N'||kind=='V'||kind=='T')?0:(kind=='R'||kind=='Q'||kind=='B'||kind=='W'||kind=='A'||kind=='L'?1:2),h=atomic_load_explicit(&cp_ring[i].head,memory_order_relaxed);
 if(n>CP_COLS || h-atomic_load_explicit(&cp_ring[i].tail,memory_order_acquire)>=CP_CAP){
  atomic_fetch_add(&cp_ring[i].lost,1);return;}
 CombatRow *r=&cp_ring[i].rows[h%CP_CAP];r->kind=kind;r->n=n;memcpy(r->v,v,n*sizeof(*v));
 atomic_store_explicit(&cp_ring[i].head,h+1,memory_order_release);
}
#ifdef NGB_NATIVE_DIAG
// All three callbacks run on the guest worker. Keep cumulative nanoseconds so
// short transfers aren't rounded down individually.
struct CombatIO { uint64_t ops,bytes,ns; };
static struct CombatIO cp_read,cp_write,cp_archive;
static unsigned cp_guest_frame;
static uint64_t cp_menu_until;
static uint64_t cp_mission_until;
static int cp_entered_game;
static atomic_int cp_main_menu;
void ngb_combat_menu_visible(int visible){atomic_store_explicit(&cp_main_menu,visible,memory_order_relaxed);}
void ngb_combat_file(int write,int archive,uint32_t bytes,uint64_t ns){
 struct CombatIO *io=write?&cp_write:&cp_read;
 ++io->ops;io->bytes+=bytes;io->ns+=ns;
 if(write && archive){++cp_archive.ops;cp_archive.bytes+=bytes;cp_archive.ns+=ns;}
}
void ngb_combat_new_game_press(void){
 uint64_t now=ngb_elapsed_ns()/1000;
 uint64_t v[]={cp_guest_frame,now};
 ngb_combat_row('J',v,2);
 cp_menu_until=now+10000000;
}
void ngb_combat_mission_press(void){
 uint64_t now=ngb_elapsed_ns()/1000;
 uint64_t v[]={cp_guest_frame,now,1};
 ngb_combat_row('M',v,3);
 cp_mission_until=cp_menu_until=now+15000000;
}
static uint16_t combat_u16(const uint8_t *p){uint16_t v;memcpy(&v,p,sizeof v);return v;}
static uint32_t combat_u32(const uint8_t *p){uint32_t v;memcpy(&v,p,sizeof v);return v;}

static void combat_player(unsigned frame,const uint8_t *ram){
 unsigned actor=ram[0x4b7640];
 if(actor>=32)return;
 // sub_00023520 checks the action byte at +4. Keep both action fields to
 // resolve the transition from charging to the weapon's release animation.
 const uint8_t *action=ram+0x4968b0+actor*0xdd0u;
 unsigned pad=ram[0xdb932e];
 const uint8_t *input=pad<5?ram+0xd219a0+pad*0x78u:NULL;
 // sub_000EBAB0 allocates these 40 slots. The E2 and B0 initializers put
 // the character at +0xf8 and its equipped weapon object at +0xf4.
 unsigned e2=0,b0=0;
 uint64_t types[4]={0};
 for(unsigned i=0;i<40;++i){
  const uint8_t *fx=ram+0x5b6930+i*0x180u;
  if(!fx[0x178])continue;
  unsigned type=fx[0x17a];
  types[type/64]|=UINT64_C(1)<<(type%64);
  if(combat_u32(fx+0xf8)==0x4b4e50u){e2+=type==0xe2;b0+=type==0xb0;}
 }
 uint64_t state[]={frame,action[0],action[4],combat_u16(ram+0x58a570+actor*0x210u),
  input?combat_u32(input):0,input?combat_u32(input+8):0,
  combat_u16(ram+0x5895e2),combat_u16(ram+0x5895e4),
  combat_u16(ram+0x5895e6),combat_u16(ram+0x5895e8),
  combat_u32(ram+0x5a2130),combat_u16(ram+0xdb9c6e),
  combat_u32(ram+0x4b5710),combat_u32(ram+0x4b5714),combat_u32(ram+0x4b5718),e2,b0,
  types[0],types[1],types[2],types[3]};
 ngb_combat_row('U',state,sizeof state/sizeof *state);
}
#endif
void ngb_combat_guest(unsigned frame,unsigned id,unsigned mode,unsigned diff,unsigned hp,unsigned maxhp,
 unsigned display,uint64_t ops,uint64_t bytes,uint64_t io,const uint8_t *ram){
 int on=(id==23 && mode==3) || (id==255 && mode==0 && maxhp>0);
#ifdef NGB_NATIVE_DIAG
 cp_guest_frame=frame;
 if(atomic_load_explicit(&cp_main_menu,memory_order_relaxed))on=1;
 if(cp_mission_until){
  uint64_t now=ngb_elapsed_ns()/1000;
  if(now>cp_mission_until)cp_mission_until=0;
  else if(ram && combat_u32(ram+0xc07378)==1 && combat_u32(ram+0xc0737c)==1){
   uint64_t v[]={frame,now,2};
   ngb_combat_row('M',v,3);
   cp_mission_until=0;
  }
 }
 // Results can clear the mission and player before their effects finish.
 // Once a stage starts, keep the opt-in recorder active through the transition.
 if((id!=255 && mode==3) || (id==255 && mode==1))cp_entered_game=1;
 if(cp_entered_game){on=1;cp_menu_until=0;}
 else if(cp_menu_until){if(ngb_elapsed_ns()/1000<=cp_menu_until)on=1;else cp_menu_until=0;}
#else
 (void)ram;
#endif
 int prev=atomic_exchange_explicit(&cp_active,on,memory_order_relaxed);
 if(on || prev){uint64_t v[]={frame,ngb_elapsed_ns()/1000,ngb_combat_cpu_us(),id,mode,diff,hp,maxhp,display,ops,bytes,io,on
#ifdef NGB_NATIVE_DIAG
 ,cp_read.ops,cp_read.bytes,cp_read.ns/1000,cp_write.ops,cp_write.bytes,cp_write.ns/1000,
 cp_archive.ops,cp_archive.bytes,cp_archive.ns/1000,ram?combat_u16(ram+0xdb9c6e):UINT16_MAX
#endif
 };
 ngb_combat_row('G',v,sizeof v/sizeof *v);}
#ifdef NGB_NATIVE_DIAG
 if(on && ram && maxhp)combat_player(frame,ram);
#endif
}
static int combat_requested(const char *path){
 struct stat st;
 return stat(path,&st)==0 && S_ISREG(st.st_mode);
}
static int combat_open(const char *path){
 cp_file=fopen(path,"a+");if(!cp_file)return 0;
#ifdef NGB_NATIVE_DIAG
 cp_entered_game=0;cp_mission_until=cp_menu_until=0;
 ngb_combat_menu_visible(0);
#endif
 setvbuf(cp_file,cp_file_buffer,_IOFBF,sizeof cp_file_buffer);
 fprintf(cp_file,"#SESSION,0.56.25,clock_us=monotonic,cpu_us=thread_total_or_zero\n"
 "#G,guest_flip,time_us,cpu_us,mission_id,mode,difficulty,hp,max_hp,display_total,io_ops_total,io_bytes_total,io_us_total,active"
#ifdef NGB_NATIVE_DIAG
 ",read_ops,read_bytes,read_us,write_ops,write_bytes,write_us,archive_write_ops,archive_write_bytes,archive_write_us,event_id"
#endif
 "\n"
 "#R,present,time_us,cpu_us,draw_calls,drawn,descriptor_requests,writes,geometry_bytes,reused_bytes,shaders,pipelines,compile_us,texture_uploads,texture_us,max_tex_us,max_tex_w,max_tex_h,max_tex_fmt,queue_us,fence_us,publish_us,present_us,rt_changes,small_rt_draws,blend_draws,indices,draw_samples,sampled_draw_wall_us,sampled_draw_cpu_us,gpu_query_slots,guest_wait_us_total\n"
 "#Q,submit_frame,read_time_us,gpu_us,valid"
#ifdef NGB_NATIVE_DIAG
 ",gpu_start_ns,gpu_end_ns,writes_screen"
#endif
 "\n"
 "#D,generation,time_us,acquire_us,blit_overlay_us,submit_us\n"
 "#P,time_us,renderer,pc_offset,lr_offset,pause_cost_us,rc\n"
 "#C,time_us,cpu_hz,gpu_hz,emc_hz,cpu_rc,gpu_rc,emc_rc\n"
 "#F,time_us,write_us,rows\n"
#ifdef NGB_NATIVE_DIAG
 "#I,issue_us,read_start_us,read_end_us,preload_end_us,published_us,guest_copy_us,handle,basename_fnv1a,offset,requested,received,status\n"
 "#H,begin_us,generation_before,generation_after,slot_wait_us,image_wait_us,slot_ready,image_ready,dequeue_us,release_event_us,release_fence_us,dequeue_calls,release_event_calls,release_fence_calls\n"
 "#O,time_us,min_images,max_images,requested_images,actual_images,command_slots,present_mode"
#ifdef __SWITCH__
 ",native_swap_interval"
#endif
 "\n"
 "#Y,begin_us,generation_after_acquire,queue_lock_us,queue_submit_us,queue_present_us,window_gpu_ns,valid,source_frame,image_index,scene_submit_us,window_submit_us,queue_present_end_us,gpu_start_ns,gpu_end_ns,present_result\n"
 "#K,host_before_us,gpu_ns,host_after_us,result\n"
 "#S,wait_start_us,vsync_wake_us\n"
 "#J,last_guest_flip,new_game_press_us\n"
 "#M,guest_flip,time_us,event_1_mission_press_2_grid_ready\n"
 "#W,submit_frame,strip_draws,sprite_draws,strip_sampled,sprite_sampled,strip_gpu_ns,sprite_gpu_ns,unavailable\n"
 "#A,submit_frame,material_detail,spans,omitted_calls,valid,opaque_calls,alpha_calls,additive_calls,offscreen_calls,composite_calls,history_calls,scanout_calls,opaque_ns,alpha_ns,additive_ns,offscreen_ns,composite_ns,history_ns,scanout_ns,feedback_calls,surface_copy_calls,feedback_ns,surface_copy_ns,feedback_pixels,surface_copy_pixels,screen_mix_calls,screen_mix_ns,add128_calls,add128_ns,ring_target_calls,ring_target_ns\n"
 "#L,submit_frame,phase,texture_sig,width,height,format,src,dst,calls,spans,gpu_ns,pixel_shader,texture1_sig,target_stages\n"
 "#U,guest_flip,action_field_0,action_kind,melee_item,pad_state,pad_edges,charge_level,charge_ticks,et_mark,ut_mark,charge_fx_flag,event_id,player_x_f32bits,player_y_f32bits,player_z_f32bits,ryu_fx_e2,ryu_fx_b0,fx_types_0,fx_types_64,fx_types_128,fx_types_192\n"
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
#ifdef NGB_VI_VSYNC_TRACE
 ViDisplay display={0};
 Event vsync={0};
 Result rc=viOpenDefaultDisplay(&display);
 if(R_SUCCEEDED(rc))rc=viGetDisplayVsyncEvent(&display,&vsync);
 if(R_FAILED(rc))fprintf(cp_file,"#VSYNC_ERROR,%u\n",(unsigned)rc);
#endif
 while(!atomic_load_explicit(&cp_writer_stop,memory_order_acquire)){
  combat_flush(0);
#ifdef NGB_VI_VSYNC_TRACE
  if(eventActive(&vsync) && ngb_combat_active()){
   // Record the waiting interval as well as the wake. An already signalled
   // event after an SD flush cannot date that refresh edge.
   uint64_t before=ngb_elapsed_ns()/1000;
   rc=eventWait(&vsync,25000000);
   if(R_SUCCEEDED(rc)){
    uint64_t after=ngb_elapsed_ns()/1000;
    fprintf(cp_file,"S,%" PRIu64 ",%" PRIu64 "\n",before,after);
   }else if(R_VALUE(rc)!=KERNELRESULT(TimedOut)){
    fprintf(cp_file,"#VSYNC_ERROR,%u\n",(unsigned)rc);
    eventClose(&vsync);
   }
   continue;
  }
#endif
  svcSleepThread(10000000);
 }
#ifdef NGB_VI_VSYNC_TRACE
 if(eventActive(&vsync))eventClose(&vsync);
 if(display.initialized)viCloseDisplay(&display);
#endif
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
