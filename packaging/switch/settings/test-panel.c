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
static void key(unsigned k){PadState pad={k,k};assert(settings_input(&pad));}
int main(int argc,char**argv){
 assert(argc==2);ngb_fast_ram=calloc(1,0x1000000);prefs_load();assert(pref(24)&&!pref(44));atomic_store(&panel,PANEL);key(0);
 /* Enter each category and scroll every row, including fixed targets and the
  * last controls row. The first/last page navigation must wrap independently. */
 for(unsigned c=0;c<PAGES;c++){
   key(1);unsigned n=0;for(unsigned j=0;j<COUNT;j++)n+=settings[j].page==c;
   for(unsigned j=0;j<n;j++){unsigned v=atomic_load(&panel);assert(((v>>8)&255)==c+1 && (v&255)==j);draw_settings(NULL,v);key(8);}
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
   int mode=ngb_bow_aiming();assert(mode==(i==4?2:1));atomic_store(&aim,mode);memset(pixels_out,0,sizeof pixels_out);game_overlay(pixels_out,1280);
   unsigned max=0;int bestx=0,besty=0;for(int y=345;y<385;y++)for(int x=625;x<665;x++){unsigned p=pixels_out[y*1280+x];unsigned l=(p&255)+(p>>8&255)+(p>>16&255);if(l>max)max=l,bestx=x,besty=y;}
   assert(max>400 && abs(bestx-(640+(mode==1?9:0)))<=2 && abs(besty-(360+(mode==1?9:0)))<=2);
 }
 MEM16(0x58a572)=1;assert(!ngb_bow_aiming());MEM16(0x58a572)=0xf8;atomic_store(&value[24],0);assert(!ngb_bow_aiming());atomic_store(&value[24],1);
 ngb_camera_frame();ngb_camera_frame();assert(!ngb_bow_aiming());s_fp_seen=s_frame;MEM8(0x4b7640)=32;assert(!ngb_bow_aiming());
 printf("PASS: %d settings, menu -> persisted bow setting; real game sprite, four bows + Strongbow, HUD, view timeout and no player.\n",(int)COUNT);
}
