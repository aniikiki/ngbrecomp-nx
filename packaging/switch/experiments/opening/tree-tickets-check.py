"""Exercise the two poll sequences taken directly from the original and trial include."""
from pathlib import Path
import subprocess,tempfile,runpy
p=Path(__file__).parent
old=Path('packaging/switch/runtime/tree_insert.inc').read_text()
new=runpy.run_path(str(p/'tree-tickets.py'))['transform']('#include "tree_insert.inc"')
a=new.index('unsigned n =');b=new.index('frame[-3]',a)
pre='''#include <stdint.h>
#include <assert.h>
static uint64_t ngb_guest_polls, trace[2]; static unsigned ngb_pending_dpcs, ngb_poll_mask,len;
static void ngb_guest_block_poll(void){uint64_t t=++ngb_guest_polls;if(!(t&ngb_poll_mask)||ngb_pending_dpcs){trace[len++]=t;ngb_poll_mask^=3;ngb_pending_dpcs^=1;}}
'''
assert old.count('ngb_guest_block_poll();')==2
src=pre+'static void candidate(unsigned jump,int left){'+new[a:b]+'}\n'+'''
int main(){for(unsigned m=0;m<256;m++)for(unsigned t=0;t<256;t++)for(unsigned c=0;c<16;c++){
unsigned jump=c&1?0x00308c8e:0x00308c6d,left=!!(c&2),d=!!(c&4);
uint64_t start=(c&8?UINT64_MAX-127:0)+t;
ngb_guest_polls=start;ngb_poll_mask=m;ngb_pending_dpcs=d;len=0;
if(jump!=0x00308c8e)ngb_guest_block_poll();if(!left)ngb_guest_block_poll();
uint64_t end=ngb_guest_polls, a=trace[0],b=trace[1];unsigned count=len,mask=ngb_poll_mask,pend=ngb_pending_dpcs;
ngb_guest_polls=start;ngb_poll_mask=m;ngb_pending_dpcs=d;len=0;trace[0]=trace[1]=0;
candidate(jump,left);assert(end==ngb_guest_polls&&len==count&&mask==ngb_poll_mask&&pend==ngb_pending_dpcs);
assert((!count||trace[0]==a)&&(count<2||trace[1]==b));
}}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'check.c';f.write_text(src);out=f.with_suffix('')
 subprocess.run(['cc','-O2',f,'-o',out],check=True);subprocess.run([out],check=True)
print('1048576 ticket/mask/branch/callback combinations passed')
