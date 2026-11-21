/* Host fixture: real settings, camera predicate and retail sprite. No Switch or save access. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <stdatomic.h>
#include <sys/stat.h>
#include "runtime.h"
#include "frontend_input.h"
#include "scanout.h"
#include "src/camera.c"
unsigned char *ngb_fast_ram;
uint16_t ngb_fast_page_bytes[1u<<20];
uintptr_t ngb_guest_scalar_fallback(uint32_t a,size_t n){assert(a+n<0x1000000);return (uintptr_t)(ngb_fast_ram+a);}
int xbox_mod_file(const char*a,char*b,size_t c){return 0;}
typedef uint32_t u32;typedef uint64_t u64;
typedef struct{u64 held,down;}PadState;typedef int Framebuffer;
enum{HidNpadButton_A=1,HidNpadButton_B=2,HidNpadButton_Plus=4,HidNpadButton_AnyDown=8,HidNpadButton_AnyUp=16,HidNpadButton_AnyLeft=32,HidNpadButton_AnyRight=64,HidNpadButton_X=128,HidNpadButton_Minus=256};
#define padGetButtons(p) ((p)->held)
#define padGetButtonsDown(p) ((p)->down)
static u32 pixels_out[1280*720];static u64 timer;
#define framebufferBegin(f,s) (*(s)=5120,(void)(f),pixels_out)
#define framebufferEnd(f) (void)(f)
#define armGetSystemTick() (++timer)
#define armGetSystemTickFreq() 1000000ull
#define ngb_scanout_blit(...) ((void)0)
#define ngb_ohci_pad_sample(...) ((void)0)
#define svcSleepThread(...) ((void)0)
static atomic_uint commands;
static bool envHasNextLoad(void){return false;}
static int envSetNextLoad(const char *path,const char *args){(void)path;(void)args;return 1;}
#define R_FAILED(rc) ((rc)!=0)
#define NGB_GPU_PRESENT 1
static unsigned displayed;
unsigned ngb_scanout_display_count(void){return displayed;}
int ngb_scanout_is_gpu(void){return 1;}
int ngb_scanout_is_blank(void){return 0;}
const uint32_t *ngb_scanout_last_pixels(void){abort();}
#include "packaging/switch/runtime/settings_panel.inc"
void ngb_switch_sample_quick(unsigned v){(void)v;}
int ngb_pc_setting(int id){return ngb_switch_setting(id);}
int ngb_movie_owns_input(void){return 0;}
/* Execute the lifted death check with only its inventory and revive calls stubbed. */
RECOMP_TLS RecompRegs g_regs;
static unsigned owned,revived,lookups;
static void consume_talisman(void){assert(eax==0xfb && ebx==UINT32_MAX && owned);owned--;esp+=4;}
void sub_001542C0(void){assert(esi==0xfb);lookups++;eax=owned;esp+=4;}
void sub_002FD470(void){revived++;esp+=4;}
#undef RECOMP_ICALL_SAFE
#define RECOMP_ICALL_SAFE(addr,sp) do{assert((addr)==0x00154300);consume_talisman();}while(0)
#undef RECOMP_ENTRY
#define RECOMP_ENTRY(addr) ((void)0)
#include "packaging/switch/settings/talisman.c"
static void check_death(unsigned items,unsigned alive){
 owned=items;revived=lookups=0;esp=0x110000;eax=0x4B4E50;
 MEM8(eax+0x27F0)=0;MEM8(0x58A3A0+0x1F4)=1;MEM16(0x58A3A0+0x1C6)=0;
 sub_002FD3E0();
 assert((eax&255)==!alive && revived==alive && owned==items-alive && esp==0x110004);
 assert(lookups==(unsigned)pref(43));
}
/* Compare sparse GPU layers against the existing framebuffer drawing on a colored background. */
static const uint32_t background=0xff864221;
int ngb_display_present(const NgbScreenFrame *frame,uint64_t times[3]){
 (void)times;assert(frame->gpu && !frame->cpu_bgra);
 for(unsigned y=0;y<720;y++)for(unsigned x=0;x<1280;x++){
    uint32_t over=0;
    for(unsigned r=0;r<frame->count;r++){
        NgbScreenRect b=frame->rects[r];
        if(x>=b.x && x<b.x+b.w && y>=b.y && y<b.y+b.h)over=frame->overlay_rgba[y*1280+x];
    }
    for(int k=0;k<24;k+=8){
        int got=((over>>k)&255)+(((background>>k)&255)*(255-(over>>24))+127)/255;
        assert(abs(got-(int)((pixels_out[y*1280+x]>>k)&255))<=2);
    }
 }
 return 1;
}
static void compare_display(unsigned view){
 for(unsigned i=0;i<1280*720;i++)pixels_out[i]=background;
 if(view&EXIT_PANEL)draw_exit_panel(NULL,view);
 else if(view)draw_settings(NULL,view);
 else game_overlay(pixels_out,1280,NULL);
 assert(present_screen(view,NULL)==1);
}
static void key(unsigned k){PadState pad={k,k};assert(settings_input(&pad));}
int main(int argc,char**argv){
 assert(argc==2);ngb_fast_ram=calloc(1,0x1000000);prefs_load();assert(ngb_bind_third_person_start());
 FILE *legacy=fopen(PREF_FILE,"w");assert(legacy);fputs("third_person=0\nthird_y=1\n",legacy);assert(!fclose(legacy));
 prefs_load();assert(ngb_bind_third_person_start() && pref(51));
 assert(prefs_save(46,0));prefs_load();assert(!ngb_bind_third_person_start() && pref(51));
 assert(prefs_save(255,0));assert(ngb_bind_third_person_start() && !pref(51));
 assert(pref(24)&&!pref(44));atomic_store(&panel,PANEL);key(0);
 /* Enter each category and scroll every row, including fixed targets and the
  * last controls row. The first/last page navigation must wrap independently. */
 for(unsigned c=0;c<PAGES;c++){
   key(1);unsigned n=0;for(unsigned j=0;j<COUNT;j++)n+=settings[j].page==c;
   for(unsigned j=0;j<n;j++){unsigned v=atomic_load(&panel);assert(((v>>8)&255)==c+1 && (v&255)==j);draw_settings(NULL,v);if(j==0 || j+1==n)compare_display(v);key(8);}
   assert((atomic_load(&panel)&255)==0);key(2);key(8);
 }
 assert(prefs_save(68,13));assert(pref(68)==13);assert(prefs_save(255,0));assert(pref(68)==8);
 atomic_store(&value[11],1);assert(prefs_save(18,1));prefs_load();assert(!pref(11) && pref(18));
 for(int i=0;i<GAMEPLAY;i++)key(HidNpadButton_AnyDown);key(1);
 for(int i=0;i<6;i++)key(8);
 assert(pref(43));check_death(1,1);check_death(0,0);
 key(1);assert(!pref(43));check_death(1,0);
 atomic_store(&value[43],1);prefs_load();assert(!pref(43));key(8);key(1);assert(pref(44));key(2);key(4);key(0);assert(!atomic_load(&panel));
 atomic_store(&value[44],0);prefs_load();assert(pref(44));
 ngb_quick_set_game_dir(argv[1]);bow_loaded=ngb_crosshair_picture(bow_art,64);assert(bow_loaded);
 s_fp_seen=s_frame;
 for(int i=0;i<5;i++){
   unsigned ids[]={0x27,0x29,0x8d,0xe2,0xf8};MEM16(0x58a572)=ids[i];
   int mode=ngb_bow_aiming();assert(mode==(i==4?2:1));atomic_store(&aim,mode);memset(pixels_out,0,sizeof pixels_out);game_overlay(pixels_out,1280,NULL);
   unsigned max=0;int bestx=0,besty=0;for(int y=345;y<385;y++)for(int x=625;x<665;x++){unsigned p=pixels_out[y*1280+x];unsigned l=(p&255)+(p>>8&255)+(p>>16&255);if(l>max)max=l,bestx=x,besty=y;}
   assert(max>400 && abs(bestx-(640+(mode==1?9:0)))<=2 && abs(besty-(360+(mode==1?9:0)))<=2);
 }
 compare_display(0);
 /* UI retries must leave the rate tied to frames actually presented. */
 atomic_store(&value[5],1);game_overlay(pixels_out,1280,NULL);
 timer+=500000;displayed+=20;compare_display(0);
 compare_display(EXIT_PANEL|EXIT_CONFIRM|1);
 atomic_store(&exit_preview,true);compare_display(0);atomic_store(&exit_preview,false);
 MEM16(0x58a572)=1;assert(!ngb_bow_aiming());MEM16(0x58a572)=0xf8;atomic_store(&value[24],0);assert(!ngb_bow_aiming());atomic_store(&value[24],1);
 ngb_camera_frame();ngb_camera_frame();assert(!ngb_bow_aiming());s_fp_seen=s_frame;MEM8(0x4b7640)=32;assert(!ngb_bow_aiming());
 printf("PASS: %d settings, menu -> persisted bow setting; real game sprite, four bows + Strongbow, HUD, view timeout and no player.\n",(int)COUNT);
}
