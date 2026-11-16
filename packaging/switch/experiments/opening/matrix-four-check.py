"""Check actual NEON block against scalar x87 operation order and wrapped poll tickets."""
from pathlib import Path
import tempfile,subprocess
p=Path(__file__).resolve().parent
h=(p.parents[1]/'runtime/arm_math.h').read_text()
test=r'''
#include <arm_neon.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
static uint64_t ngb_guest_polls;
static unsigned ngb_poll_mask,ngb_pending_dpcs,g_fp_control_word,g_fp_top;
static double g_fp_stack[8];
static float ram[128];
static void*ngb_ram_span(unsigned a,unsigned n){return a<=sizeof ram-n?(char*)ram+a:0;}
''' +h[h.index('static inline uint32x4_t ngb_arm_dot_range'):h.index('static inline bool ngb_arm_x87_row')] +(p/'matrix-four.h').read_text()+r'''
static unsigned seed=917;
static uint32_t rng(void){return seed=1664525*seed+1013904223;}
int main(void){unsigned hit=0,miss=0;
for(unsigned n=0;n<50000;n++){
 unsigned l=32,r=n%11==0?32:112,d=n%9==0?36:n%19==0?600:n%37==0?201:204;
 for(unsigned j=0;j<128;j++){uint32_t w=(rng()&0x807fffff)|((97+rng()%60)<<23);
 if(j%17==n%17)w&=0x80000000u;
 memcpy(ram+j,&w,4);}
 if(n%23==0){uint32_t inf=0x7f800000;memcpy(ram+l/4,&inf,4);}
 unsigned top=g_fp_top=n%8;for(unsigned j=0;j<8;j++)g_fp_stack[j]=rng();
 uint64_t ticket=ngb_guest_polls=n%2?UINT64_MAX-(n%67):n;
 ngb_poll_mask=n%13==0?47:n%7==0?15:63;ngb_pending_dpcs=n%29==0;g_fp_control_word=n%17==0?0x300:0;
 double slots[8];memcpy(slots,g_fp_stack,sizeof slots);float ref[128];memcpy(ref,ram,sizeof ref);
 bool ok=ngb_matrix_four(l,r,d);
 if(ok){
 if(ngb_pending_dpcs||g_fp_control_word||d!=204||ngb_guest_polls!=ticket+19)abort();
 for(unsigned j=1;j<=19;j++)if(!((ticket+j)&ngb_poll_mask))abort();
 for(unsigned i=0;i<4;i++){
 for(unsigned k=0;k<4;k++){top=(top+7)&7;slots[top]=ref[l/4+i*4+k];}
 for(unsigned lane=0;lane<4;lane++){
 float prod[4];for(unsigned k=0;k<4;k++)prod[k]=(float)(slots[(top+3-k)&7]*ref[r/4+4*k+lane]);
 float odd=prod[1]+prod[3],v=(prod[2]+prod[0])+odd;
 slots[(top+4)&7]=prod[0];slots[(top+5)&7]=prod[3];slots[(top+6)&7]=odd;slots[(top+7)&7]=v;
 ref[d/4+4*i+lane]=v;
 }}hit++;
 }else{miss++;if(ticket!=ngb_guest_polls)abort();}
 if(g_fp_top!=top||memcmp(ref,ram,sizeof ram)||memcmp(slots,g_fp_stack,sizeof slots))abort();
}printf("matrix-four %u accepted, %u fallback; full RAM, x87 slots and polls agree\n",hit,miss);return hit<1000;}
'''
with tempfile.TemporaryDirectory() as td:
 f=Path(td)/'test.c';f.write_text(test);exe=f.with_suffix('')
 subprocess.run(['cc','-O2','-ffp-contract=off',f,'-o',exe],check=True);subprocess.run([exe],check=True)
