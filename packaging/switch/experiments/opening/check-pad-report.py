"""Exercise actual XID reports, including A in menus and all simultaneous face-button chords."""
from pathlib import Path
import subprocess,shlex,tempfile
b=Path('/work/build/switch-runtime/host')
cmd=next(shlex.split(line) for line in subprocess.check_output(['ninja','-t','commands','ngb-runtime-test'],cwd=b,text=True).splitlines() if line.endswith('/ohci_boot.c'))
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);o=d/'pad.o'
 cmd[cmd.index('-o')+1]=str(o);cmd[cmd.index('-MF')+1]=str(d/'pad.d')
 cmd[1:1]=["-ffunction-sections","-fdata-sections"]
 subprocess.run(cmd,cwd=b,check=True)
 s=d/'test.c';s.write_text("""
#include <assert.h>
#include <stdint.h>
#include <string.h>
extern void ngb_ohci_pad_sample(uint16_t,int16_t,int16_t,int16_t,int16_t);
extern int usb_gamepad_report(int,uint8_t*,int);
uint8_t ram[0xdb9ad6], *ngb_fast_ram=ram;
uint64_t ngb_elapsed_ns(void){return 0;}
int ngb_scanout_ready(void){return 0;}
int main(void){
 for(unsigned mode=0;mode<4;mode++){
 ram[0x7f1b12]=mode==1||mode==3?1:mode;ram[0xdb9894]=2;ram[0xdb9ad5]=mode==3;
 ngb_ohci_pad_sample(0,0,0,0,0);uint8_t neutral[20];usb_gamepad_report(0,neutral,20);
 for(unsigned mask=0;mask<16;mask++){
  uint8_t report[20];ngb_ohci_pad_sample(mask<<8,1,-2,32000,-32000);
  assert(usb_gamepad_report(0,report,20)==20);
  for(int i=0;i<4;i++)assert(report[4+i]==((mask & (1u<<(mode==1?(i^1):i)))?255:0));
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
 }
""")
 subprocess.run(['cc',s,o,'-Wl,--gc-sections','-o',d/'test'],check=True)
 subprocess.run([d/'test'],check=True)
 print('64 face button reports, stick passthrough and 360 held reports across context change passed')
