"""Differential exercise of the generated packet retirement function and its lookahead contract."""
from pathlib import Path
import runpy,tempfile,subprocess
here=Path(__file__).parent;s=Path('packaging/switch/runtime/nv2a_boot.c').read_text()
t=runpy.run_path(str(here/'fifo-last-state.py'))['transform'](s)
def extract(s):
 a=s.index('static unsigned retire_state_packets');return s[a:s.index('\n}',a)+2]
pre=r'''
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#define XBOX_CONTIG_SIZE 16384
#define NV_PFIFO_CACHE1_PUSH1 4
#define NV_PFIFO_CACHE1_PULL0 8
#define NV_PGRAPH_FIFO 12
#define NV_PGRAPH_CTX_CONTROL 16
#define NV_PGRAPH_CTX_CONTROL_CHID 1
#define NV_PGRAPH_CTX_USER 20
#define NV_PGRAPH_CTX_USER_CHID 0x1f000000u
#define NV_PGRAPH_CTX_CACHE1 32
#define NV_PGRAPH_CTX_SWITCH1 256
#define NV_KELVIN_PRIMITIVE 0x97
#define NV_PFIFO_CACHE1_DMA_STATE_METHOD 0x1ffcu
static unsigned graph_regs[128],fifo_regs[128],packet_count,param_count,direct_batched_words;
static uint32_t ring[4096];static const uint8_t *ngb_contiguous_pages[4];
static unsigned ngb_target_pages[4],ngb_scene_active;
static unsigned state_packet_size(unsigned h){unsigned n=h>>18;return !(h & ~(0x1ffcu|0x1ffc0000u)) && n && n<=16?n+1:0;}
'''
code=pre+extract(s).replace('retire_state_packets','orig')+'\n'+extract(t).replace('retire_state_packets','candidate')+r'''
int main(void){unsigned seed=7,ready_total=0;
for(unsigned k=0;k<100000;k++){seed=1664525*seed+1013904223;unsigned g=(seed%1024)*4,put=g+4*(1+(k%100)),limit=(k%11==0?g+7:8191);
for(unsigned i=g/4;i<put/4;i++){seed=1664525*seed+1013904223;ring[1024+i]=(seed&1)?0x40000000u:((1+(seed%16))<<18)|4;}
if(k%3==0){for(unsigned i=g/4;i<put/4;){unsigned count=1+(i%5);ring[1024+i]=(count<<18)|((i*4)&0x1ffc);i+=1+count;}}
else ring[1024+g/4]=1u<<18;ngb_scene_active=k%37!=0;ngb_target_pages[1]=k%43==0;ngb_contiguous_pages[1]=k%13?(const uint8_t*)(ring+1024):0;
graph_regs[3]=graph_regs[4]=fifo_regs[2]=1;graph_regs[8]=k%59?0x97:0;
unsigned a=91,b=91,n=0,r=0;packet_count=param_count=direct_batched_words=0;
unsigned x=orig(ring[1024+g/4],4096,g,put,limit,&a),pk=packet_count,pm=param_count,bt=direct_batched_words;
packet_count=param_count=direct_batched_words=0;
unsigned y=candidate(ring[1024+g/4],4096,g,put,limit,&b);
if(x!=y||a!=b||pk!=packet_count||pm!=param_count||bt!=direct_batched_words)abort();
if(pk>=3)ready_total++;}
return !ready_total;}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'test.c';f.write_text(code);o=f.with_suffix('')
 subprocess.run(['cc','-O2',str(f),'-o',o],check=True);subprocess.run([o],check=True)
print('100000 retirement/final-state cases matched (synthetic packet classifier)')
