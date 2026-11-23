"""Exercise actual XID reports, including A in menus and all simultaneous face-button chords."""
from pathlib import Path
import subprocess,shlex,tempfile
b=Path('/work/build/switch-runtime/host')
cmd=next(shlex.split(line) for line in subprocess.check_output(['ninja','-t','commands','ngb-runtime-test'],cwd=b,text=True).splitlines() if line.endswith('/ohci_boot.c'))
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);o=d/'pad.o'
 cmd[cmd.index('-o')+1]=str(o);cmd[cmd.index('-MF')+1]=str(d/'pad.d')
 cmd[1:1]=["-ffunction-sections","-fdata-sections","-DNGB_NATIVE_DIAG","-include","player_diagnostics.h"]
 subprocess.run(cmd,cwd=b,check=True)
 s=d/'test.c';s.write_text("""
#include <assert.h>
#include <stdint.h>
#include <string.h>
extern void ngb_ohci_pad_sample(uint16_t,int16_t,int16_t,int16_t,int16_t);
extern int usb_gamepad_report(int,uint8_t*,int);
extern unsigned ngb_pad_movie_input(int);
extern unsigned ngb_movie_skip_edges(void);
uint8_t ram[0xdb9ad6], *ngb_fast_ram=ram;
extern void ngb_menu_draw(uint32_t);
extern void ngb_pad_flip(void);
int ngb_diagnostics_enabled=1, ngb_combat_enabled, ngb_scene_active;
static unsigned clocks, new_game, missions;
uint64_t ngb_elapsed_ns(void){return ++clocks;}
void ngb_kernel_log(const char *s){(void)s;}
void ngb_menu_gpu_report(void){}
void ngb_scene_menu_flip(int active){(void)active;}
void ngb_combat_menu_visible(int visible){(void)visible;}
void ngb_combat_new_game_press(void){++new_game;}
void ngb_combat_mission_press(void){++missions;}
int ngb_scanout_ready(void){return 0;}
static unsigned sample_buttons(unsigned held){
 uint8_t report[20];
 ngb_ohci_pad_sample(held,0,0,0,0);
 assert(usb_gamepad_report(0,report,sizeof report)==20);
 return report[2] | (report[4]?256:0) | (report[5]?512:0);
}
static void check_logo_buttons(void){
 const unsigned plus=16, a=256, b=512;
 ram[0x7f1b12]=0;
 for(unsigned i=0;i<2;i++){
   unsigned key=i?a:plus;
   assert(sample_buttons(0)==0);
   unsigned before=ngb_pad_movie_input(1);
   assert(sample_buttons(key|b)==b);
   assert(ngb_pad_movie_input(0)==before+1);
   assert(sample_buttons(key)==0);
   assert(sample_buttons(0)==0);
   assert(sample_buttons(key)==key);
 }
 /* A held before the movie is not a skip. A fresh Plus tap, already
  * released when the decoder polls, skips once. A stays down at the title. */
 unsigned before=ngb_pad_movie_input(1);
 assert(sample_buttons(a)==0 && ngb_movie_skip_edges()==before);
 assert(sample_buttons(a|plus)==0 && sample_buttons(a)==0);
 assert(ngb_movie_skip_edges()==before+1);
 ngb_pad_movie_input(0);
 assert(sample_buttons(a|plus)==plus);
 assert(sample_buttons(0)==0 && sample_buttons(a)==a && sample_buttons(0)==0);
}
static void check_menu_cursor(void){
 const unsigned rows[]={2,1,0,2};
 for(int boot=0;boot<=1;boot++){
   ngb_diagnostics_enabled=boot;
   for(int game=0;game<=1;game++){
     ngb_combat_enabled=game;
     unsigned before=clocks;
     new_game=missions=0;
     for(unsigned i=0;i<sizeof rows/sizeof rows[0];i++){
       ngb_menu_draw(rows[i]);ngb_pad_flip();
       assert(sample_buttons(256)==256 && sample_buttons(256)==256);
       assert(sample_buttons(0)==0);
     }
     assert(new_game==(unsigned)game && missions==2u*game);
     assert((clocks!=before)==boot);
   }
 }
}
int main(void){
 for(unsigned mode=0;mode<4;mode++){
 ram[0x7f1b12]=mode==1||mode==3?1:mode;ram[0xdb9894]=2;ram[0xdb9ad5]=mode==3;
 ngb_ohci_pad_sample(0,0,0,0,0);uint8_t neutral[20];usb_gamepad_report(0,neutral,20);
 for(unsigned mask=0;mask<16;mask++){
  uint8_t report[20];ngb_ohci_pad_sample(mask<<8,1,-2,32000,-32000);
  assert(usb_gamepad_report(0,report,20)==20);
  for(int i=0;i<4;i++){
   unsigned physical=(mode==1 || i>=2)?(i^1):i;
   assert(report[4+i]==((mask & (1u<<physical))?255:0));
  }
  const int16_t sticks[]={1,-2,32000,-32000};assert(!memcmp(sticks,report+12,8));
 }
 }
 uint8_t r[20];ngb_ohci_pad_sample(0,0,0,0,0);usb_gamepad_report(0,r,20);
 ram[0xdb9ad5]=0;ram[0x7f1b12]=1;
 for(int frame=0;frame<360;frame++){
   ram[0x7f1b11]=(frame>=200 && frame<240);
   ngb_ohci_pad_sample(1u<<10,0,0,0,0);
   usb_gamepad_report(0,r,20);assert(r[7]==255 && !r[6]);
 }
 ngb_ohci_pad_sample(0,0,0,0,0);usb_gamepad_report(0,r,20);assert(!r[7] && !r[6]);
 check_logo_buttons();
 check_menu_cursor();
 }
""")
 subprocess.run(['cc',s,o,'-Wl,--gc-sections','-o',d/'test'],check=True)
 subprocess.run([d/'test'],check=True)
 print('64 face button reports, sticks, held controls across contexts, startup logo skip/release, and independent boot/game menu recording passed')
