"""Check both actual C hooks under re-entrant register changes and ESP wraparound."""
from pathlib import Path
import tempfile,subprocess,runpy
p=Path(__file__).parent;spec=runpy.run_path(str(p/'hle-scalar-call.py'))
s=Path('packaging/switch/runtime/direct/hooks.c').read_text()
def hook(s,n):return s[s.index('int d3d_hook(int fn)'):s.index('void d3d_after(int fn)')].replace('d3d_hook(',n+'(')
c='''
#include <stdint.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
static uint32_t r[8],trace,step,ram[2];
#define D3DF_Direct3D_CreateDevice 1
#define D3DF_D3DDevice_Swap 2
#define MEM32(a) ram[(a)==0x3D9588]
#define NGB_DIRECT_KICKOFF_KIB 256u
static void mutate(int n){for(unsigned i=0;i<8;i++)r[i]=r[i]*33u+(uint32_t)n;trace=trace*31+n;}
static void track_draw_call(int fn,int e){mutate(fn+e);}
static void d3d_hle_frame_wait(void){mutate(17);}
static uint32_t ngb_before_scalar(int f,uint32_t a,uint32_t c,uint32_t d,uint32_t b,uint32_t sp,uint32_t si){trace^=a+7*c+3*d+9*b+sp+11*si;mutate(f);return step;}
static int d3d_hle_call(int f,uint32_t v[8]){uint32_t n=ngb_before_scalar(f,v[0],v[1],v[2],v[3],v[4],v[6]);if(n){v[0]=0;v[4]+=n;}return n!=0;}
'''
for i,n in enumerate(('eax','ecx','edx','ebx','esp','g_ebp','esi','edi')):c+=f'#define {n} r[{i}]\n'
c+=hook(s,'original')+hook(spec['hooks'](s),'candidate')+'''
int main(void){for(unsigned i=0;i<256;i++)for(int f=0;f<4;f++)for(int m=0;m<3;m++){
 uint32_t init[8],out[8],mem[2],tr;for(unsigned j=0;j<8;j++)init[j]=i*987654321u+j*45678321u;init[4]=0xffffffffu-i;
 memcpy(r,init,sizeof r);trace=0;memset(ram,0,sizeof ram);step=m==0?0:m==1?4:12;
 int ret=original(f);memcpy(out,r,sizeof r);memcpy(mem,ram,sizeof ram);tr=trace;
 memcpy(r,init,sizeof r);trace=0;memset(ram,0,sizeof ram);assert(ret==candidate(f));
 assert(!memcmp(out,r,sizeof r)&&!memcmp(mem,ram,sizeof ram)&&tr==trace);
}return 0;}
'''
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'test.c';f.write_text(c);exe=f.with_suffix('');subprocess.run(['cc','-std=c11','-O2',f,'-o',exe],check=True);subprocess.run([exe],check=True)
print('3072 hook state/dispatch comparisons passed')
