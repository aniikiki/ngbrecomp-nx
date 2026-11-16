"""Compile actual pre/post blocks; compare destination, registers and modified RAM."""
import tempfile,subprocess,runpy
from pathlib import Path
p=Path(__file__).parent
s=Path('build/switch-runtime/gen/recomp_0010.c').read_text()
t,_=runpy.run_path(str(p/'contact-axis.py'))['transform'](s)
c=r'''
#include <math.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
typedef union {float f[4];uint32_t u[4];} X;
static struct G{uint32_t eax_,esp_,esi_,edi_,edx_,fa,fb;int fas,fbs;double fca,fcb;X x[5];} g;
static unsigned char ram[16384],save[16384],refmem[16384],*ngb_fast_ram=ram;
static uint16_t ngb_fast_page_bytes[1<<20];static float constant;
static void *ptr(uint32_t a){if(a==0x4149C4)return &constant;return ram+(a&16383);}
#define MEMF(a) (*(volatile float*)ptr(a))
#define MEM16(a) (*(volatile uint16_t*)ptr(a))
#define MEM32(a) (*(volatile uint32_t*)ptr(a))
#define XMM_SCALAR(a) ((X){.f={(a),0,0,0}})
#define CMP_BE(a,b) ((a)<=(b))
'''
for n in ('eax','esp','esi','edi','edx'):c+=f'#define {n} g.{n}_\n'
for n in ('fa','fb','fas','fbs','fca','fcb'):c+=f'#define _{n} g.{n}\n'
for i in range(5):c+=f'#define xmm{i} g.x[{i}]\n'
for n,x in enumerate((s,t)):
 a=x.index('loc_00140D7B: ;');b=x.index('loc_00140E34: ;',a)
 c+=f'static int b{n}(void){{\n'+x[a:b]+'loc_00140E34:return 1;loc_00140FC1:return 2;}\n'
c+=r'''
int main(void){unsigned n=0,pass=0;
for(unsigned off=0;off<2;off++)for(unsigned so=0;so<2;so++)for(unsigned mask=0;mask<4;mask++)for(unsigned alias=0;alias<4;alias++)for(unsigned v=0;v<256;v++){
 memset(ram,0,sizeof ram);memset(&g,0,sizeof g);memset(ngb_fast_page_bytes,0,sizeof ngb_fast_page_bytes);
 eax=(off?4056:128)|(alias&1?0x80000000:0);esp=(so?8136:6100)|(alias&2?0x80000000:0);
 ngb_fast_page_bytes[(eax+32)>>12]=mask&1?4096:0;
 ngb_fast_page_bytes[(esp+48)>>12]=mask&2?4096:0;
 for(int i=0;i<3;i++){float val=(v>>(2*i))&3;MEMF(eax+32+4*i)=val==3?NAN:val==2?-4:val;MEMF(eax+48+4*i)=2;MEMF(esp+48+4*i)=0;}
 constant=.5f;g.x[3].f[0]=v&64?0:1;MEM16(eax)=v&128;esi=93;
 struct G initial=g;memcpy(save,ram,sizeof ram);int a=b0();struct G after=g;memcpy(refmem,ram,sizeof ram);
 g=initial;memcpy(ram,save,sizeof ram);int b=b1();assert(a==b&&!memcmp(&after,&g,sizeof g)&&!memcmp(ram,refmem,sizeof ram));pass+=(a==1);n++;
}printf("%u matched; %u continued, %u exited\n",n,pass,n-pass);}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'test.c';e=f.with_suffix('');f.write_text(c)
 subprocess.run(['cc','-O2','-fno-strict-aliasing',str(f),'-o',str(e)],check=True);subprocess.run([e],check=True)
