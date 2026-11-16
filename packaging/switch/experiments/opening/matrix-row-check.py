"""Compare candidate output RAM and all physical x87 slots to four scalar dots
on ARM, including in-place and transposed layouts, exceptional inputs and polls."""
from pathlib import Path
import tempfile,runpy,subprocess as sp
p=Path(__file__).resolve().parent
h=runpy.run_path(str(p/'matrix-row.py'))['header']((p.parents[1]/'runtime/arm_math.h').read_text())
body=h[h.index('static inline bool ngb_arm_finite'):h.index('/* Transform three')]
test=r'''
#include <arm_neon.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
static unsigned ngb_pending_dpcs,ngb_poll_mask=63,ngb_guest_polls,g_fp_top,g_fp_control_word;
static double g_fp_stack[8];static float ram[96];
static void*ngb_ram_span(unsigned a,unsigned n){return a<=sizeof(ram)-n?(char*)ram+a:0;}
''' +body+r'''
static uint32_t seed=9;
static unsigned rng(void){seed=1664525u*seed+1013904223u;return seed;}
static float value(unsigned wide){unsigned u=rng();if(!wide)return (int32_t)u*0x1p-27f;u=(u&0x807fffff)|((rng()%255)<<23);float f;memcpy(&f,&u,4);return f;}
static double roundpc(double v){return g_fp_control_word?v:(double)(float)v;}
int main(void){unsigned hits=0,inplace=0,widehits=0;
 for(unsigned n=0;n<100000;n++){
  unsigned mode=n%8,w=n%3==0,t=rng()%8,src=16,dst=mode==0?16:mode==1?17:48,col=n%2;
  g_fp_top=t;g_fp_control_word=n%4<2?0:0x300;ngb_guest_polls=n%64;ngb_pending_dpcs=n%193==0;
  for(unsigned i=0;i<96;i++)ram[i]=value(w);
  for(unsigned i=0;i<8;i++)g_fp_stack[i]=value(w);
  if(n%127==0)ram[src]=NAN;
  if(g_fp_control_word && n%17==0)g_fp_stack[t]=1.0+0x1p-40;
  float ref[96];double slots[8];
  memcpy(ref,ram,sizeof ram);memcpy(slots,g_fp_stack,sizeof slots);
  unsigned before=ngb_guest_polls;
  if(!ngb_arm_x87_row(src*4,dst*4,col)){
   if(memcmp(ref,ram,sizeof ram)||memcmp(slots,g_fp_stack,sizeof slots)||ngb_guest_polls!=before)abort();
   continue;
  }
  if(ngb_pending_dpcs||before>60||g_fp_top!=t||ngb_guest_polls!=before+3)abort();
  for(unsigned lane=0;lane<4;lane++){
   double prod[4];for(unsigned i=0;i<4;i++)
    prod[i]=roundpc(slots[(t+3-i)&7]*ref[src+(col?lane*4+i:i*4+lane)]);
   double odd=roundpc(prod[1]+prod[3]),sum=roundpc(roundpc(prod[2]+prod[0])+odd);
   ref[dst+(col?4*lane:lane)]=(float)sum;
   slots[(t+4)&7]=prod[0];slots[(t+5)&7]=prod[3];slots[(t+6)&7]=odd;slots[(t+7)&7]=sum;
  }
  if(memcmp(ref,ram,sizeof ram)||memcmp(slots,g_fp_stack,sizeof slots))abort();
  hits++;inplace+=src==dst;widehits+=w&&g_fp_control_word;
 }
 printf("100000 rows; %u accepted, %u in-place, %u wide finite double-mode; RAM and all slots agree\n",hits,inplace,widehits);
 return !(inplace&&widehits);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'test.c';exe=f.with_suffix('');f.write_text(test)
 sp.run(['cc','-O2','-ffp-contract=off',f,'-o',exe],check=True);sp.run([exe],check=True)
