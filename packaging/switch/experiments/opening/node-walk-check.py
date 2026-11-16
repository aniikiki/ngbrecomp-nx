"""Compare actual generated walks up to the exit labels, including callbacks."""
from pathlib import Path
import runpy,subprocess,tempfile,sys
p=Path(__file__).parent;s=Path('build/switch-runtime/gen/recomp_0016.c').read_text()
t=runpy.run_path(str(p/(sys.argv[1] if len(sys.argv)>1 else 'node-walk.py')))['transform'](s)
def walk(s,name):
 a=s.index('loc_001CC7F8: ;');b=s.index('loc_001CC804: ;',a)
 return 'static unsigned '+name+'(void){'+s[a:b]+'loc_001CC804:return 0;loc_001CC82E:return 1;}'
src=r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>
static uint32_t ram[4096],ecx,ebp,_fa,_fb;static int32_t _fas,_fbs;
static uint64_t ngb_guest_polls;static unsigned ngb_poll_mask,ngb_pending_dpcs,calls;
static uint16_t pages[4];static uint8_t *ngb_fast_ram=(uint8_t*)ram;
#define ngb_fast_page_bytes pages
#define CMP_AE(a,b) ((a)>=(b))
#define CMP_NE(a,b) ((a)!=(b))
static uint32_t read32(uint32_t a){uint32_t v;memcpy(&v,ngb_fast_ram+(a&16383),4);return v;}
#define MEM32(x) read32(x)
static void ngb_guest_block_poll(void){if(!(++ngb_guest_polls&ngb_poll_mask)||ngb_pending_dpcs){calls++;ngb_pending_dpcs=0;ebp^=3;}}
static void init(unsigned i){ecx=(i&1?0x80000000u:0)+4096+(i%256)*16+(i%5==0);ebp=i%351;ngb_guest_polls=UINT64_MAX-i%128;calls=0;ngb_pending_dpcs=(i%17==0);ngb_poll_mask=(1u<<(i%7))-1;
pages[1]=i%3?4096:32;_fa=_fb=_fas=_fbs=0;
for(unsigned j=0;j<320;j++){unsigned a=4096+j*16+(i%5==0),link=j==319?0:(ecx&0x80000000u)+a+16;memcpy(ngb_fast_ram+a+4,&link,4);memcpy(ngb_fast_ram+a+12,&j,4);}}
'''+walk(s,'orig')+walk(t,'trial')+'''
int main(){for(unsigned i=0;i<65536;i++){init(i);unsigned r=orig(),a=ecx,b=ebp,f=_fa,g=_fb,c=calls;int x=_fas,y=_fbs;uint64_t q=ngb_guest_polls;init(i);assert(trial()==r&&a==ecx&&b==ebp&&f==_fa&&g==_fb&&x==_fas&&y==_fbs&&q==ngb_guest_polls&&c==calls);}}
'''
# Sparse alias page table; the synthetic RAM mapping uses the same physical byte offset.
src=src.replace('pages[4]','pages[1u<<20]').replace('pages[1]=i%3','pages[0x80001]=pages[1]=i%3')
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'walk.c';f.write_text(src);out=f.with_suffix('')
 subprocess.run(['cc','-O2',f,'-o',out],check=True);subprocess.run([out],check=True)
print('65536 walks matched')
