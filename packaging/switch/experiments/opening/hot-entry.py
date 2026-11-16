"""Specialize only the top 32 observed guest entries. Keep frame pointers,
event callbacks, counters, recent history and poll timing unchanged."""
from pathlib import Path
from collections import Counter
import re,os,sys
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def selection():
 s=(base/'core-perf/opening-setup/entry-mix.log').read_text()
 rows=re.findall(r'^\[ENTRY_MIX\] (\d+) (.*)$',s,re.M);assert [int(f) for f,_ in rows if 31<=int(f)<=120]==list(range(31,121))
 c=Counter()
 for f,ls in rows:
  if 31<=int(f)<=120:
   for va,n in re.findall(r'([0-9a-f]+):(\d+)',ls):c[int(va,16)]+=int(n)
 return dict(c.most_common(32))
hot=selection()
pre='''
extern __attribute__((visibility("hidden"))) uint64_t ngb_reg_entries;
extern __attribute__((visibility("hidden"))) uint32_t ngb_reg_recent[32],ngb_reg_current_va;
#define HOT_ENTRY(A) do { uint64_t e=ngb_reg_entries; \\
 if(__builtin_expect(e<48,0) || (A)==0x17a010u || (A)==0x31dc50u || (A)==0x3cc310u) ngb_checkpoint(A); \\
 else { ngb_reg_current_va=(A); ngb_reg_entries=e+1;ngb_reg_recent[e&31]=(A);ngb_guest_block_poll(); } } while(0)
'''
def transform(s):
 add=[]
 def sub(m):
  a=int(m[1],16)
  if a not in hot:return m[0]
  add.append(a);return m[0].replace('RECOMP_ENTRY','HOT_ENTRY')
 t=re.sub(r'RECOMP_ENTRY\(0x([\dA-F]+)u\);',sub,s)
 k='#include "recomp_funcs.h"';return t.replace(k,k+pre,1),add
if __name__=='__main__':
 units=[];seen=[]
 for i in range(47):
  g=transform((base/'gen'/f'recomp_{i:04}.c').read_text())[1]
  if g:units.append(i);seen+=g
 assert sorted(seen)==sorted(hot)
 print('units',units,'observed calls per frame',sum(hot.values())/90,flush=True)
 if '--build' in sys.argv:
  src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
  exec(compile('if True:'+src.replace('units=[16,28,29]','units='+repr(units)).replace('opening-vector-span','opening-hot-entry'),'hot-entry-build','exec'))
