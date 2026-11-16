"""Compile generated before/after sequences, exercise misalignment, aliases,
crossing partially mapped pages, and fallback access order for every shape."""
from pathlib import Path
import runpy,subprocess,tempfile
p=Path(__file__).with_name('vector-span.py');a=runpy.run_path(str(p));bodies={}
for u in (16,28,29):
 s=(a['base']/'gen'/f'recomp_{u:04}.c').read_text();lines=s.splitlines(True)
 for i,n in a['transform'](s)[1]:
    block=''.join(lines[i:i+n])
    for b in ('eax','ebx','ecx','edx','esp','ebp','esi','edi'):block=block.replace(b,'addr')
    bodies[block]=a['transform'](block)[0]
s=r'''
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
typedef struct{uint32_t w[4];} V;
struct State {unsigned char ram[16384];V r[8];unsigned calls,order[64];};
static struct State S,init,ref;static uint32_t addr;
static uint16_t ngb_fast_page_bytes[1u<<20];
#define ngb_fast_ram S.ram
static unsigned char *ptr(uint32_t v){if((v&4095u)+16>ngb_fast_page_bytes[v>>12])S.order[S.calls++]=v;return S.ram+(v&0x7fffffffu);}
static V XMM_MEM(uint32_t v){V x;memcpy(&x,ptr(v),16);return x;}
static void XMM_STORE(uint32_t v,V x){memcpy(ptr(v),&x,16);}
'''
s+=''.join(f'#define xmm{i} S.r[{i}]\n' for i in range(8))
for j in range(2):
 s+='static void arm'+str(j)+'(unsigned id){switch(id){\n'
 for i,z in enumerate(bodies.items()):s+=f'case {i}:{{\n'+z[j]+'}break;\n'
 s+='}}\n'
s+='int main(void){for(unsigned i=0;i<sizeof init.ram;i++)init.ram[i]=i*17u+i/13;memcpy(init.r,init.ram+11,sizeof init.r);unsigned n=0;for(unsigned id=0;id<'+str(len(bodies))+';id++)for(unsigned a=3984;a<4112;a++)for(unsigned h=0;h<2;h++)for(unsigned mode=0;mode<3;mode++){addr=a|(h<<31);for(unsigned i=0;i<4;i++)ngb_fast_page_bytes[(h<<19)+i]=mode==0?4096:mode==1?0:4087;S=init;arm0(id);ref=S;S=init;arm1(id);if(memcmp(&ref,&S,sizeof S))abort();n++;}printf("%u differential cases matched\\n",n);}'
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'span.c';f.write_text(s);exe=f.with_suffix('')
 subprocess.run(['cc','-O2',f,'-o',exe],check=True);subprocess.run([exe],check=True)
