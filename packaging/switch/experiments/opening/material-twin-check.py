"""Compare the actual generated material block; dirty/high VA fall back in original order."""
from pathlib import Path
import runpy,tempfile,subprocess
p=Path(__file__).parent;s=Path('build/switch-runtime/gen/recomp_0028.c').read_text()
def part(s):return s[s.index('loc_0030D693: ;'):s.index('loc_0030D6C5: ;')]
c=r'''
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#define NGB_RAM_BYTES (1<<24)
static unsigned char ngb_fast_ram[NGB_RAM_BYTES];
typedef uint32_t W __attribute__((aligned(1),may_alias));
#define MEM32(a) (*(volatile W*)(ngb_fast_ram+((a)&0xffffffu)))
static uint16_t ngb_fast_page_bytes[4096];
static uint32_t eax,ebx,ecx,edi,esi,_fa,_fb,g_df,calls,log_va[4];
static int32_t _fas,_fbs;
static void *ngb_guest_pointer(unsigned a,unsigned n){if(n!=68||calls>=4)abort();log_va[calls++]=a;return ngb_fast_ram+(a&0xffffffu);}
'''
c+='static void ref(void){'+part(s)+'}\nstatic void alt(void){'+part(runpy.run_path(str(p/'material-twin.py'))['transform'](s))+'}\n'
c+=r'''
int main(void){
 unsigned base=0x977b78,spans[]={0x977b78,0x3d83c8,0x901000},tests=0;
 uint8_t pre[3][768],post[3][768];uint32_t saved[9];
 for(int mode=0;mode<16;mode++)for(int off=-70;off<=70;off++)for(int j=0;j<4;j++){
 unsigned src=(j==0?base:j==1?0x3d83c8:0x901000)+off,dst=j==2?src+20:j==3?0x3d83c8:0x977b80;
 if(mode&1)src|=0x80000000;if(mode&2)dst|=0x80000000;
 for(unsigned i=0;i<3;i++)for(unsigned k=0;k<768;k++)pre[i][k]=(k*19+i*7+mode)&255;
 for(int side=0;side<2;side++){
 for(int i=0;i<3;i++)memcpy(ngb_fast_ram+spans[i]-384,pre[i],768);
 MEM32(0x3d83c8)=dst-0xf00;MEM32(0x3d83d0)=0x12345;
 ebx=src;calls=0;g_df=mode>>3;ngb_fast_page_bytes[(src&0xffffff)>>12]=ngb_fast_page_bytes[(dst&0xffffff)>>12]=mode&4?0:4096;
 if(side)alt();else ref();
 uint32_t regs[]={eax,ebx,ecx,edi,esi,_fa,_fb,(uint32_t)_fas,(uint32_t)_fbs};
 if(calls && (calls!=4||log_va[0]!=base||log_va[1]!=src||log_va[2]!=dst||log_va[3]!=src))abort();
 if(!side){memcpy(saved,regs,sizeof regs);for(int i=0;i<3;i++)memcpy(post[i],ngb_fast_ram+spans[i]-384,768);}
 else{if(memcmp(saved,regs,sizeof regs))abort();for(int i=0;i<3;i++)if(memcmp(post[i],ngb_fast_ram+spans[i]-384,768))abort();}
 }tests++;
 }printf("material twin verified %u cases\n",tests);}
'''
with tempfile.TemporaryDirectory() as td:
 f=Path(td)/'check.c';f.write_text(c);subprocess.run(['cc','-O2',str(f),'-o',td+'/check'],check=True);subprocess.run([td+'/check'],check=True)
