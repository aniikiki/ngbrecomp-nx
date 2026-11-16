"""Specialize aligned PUSH/POP in one measured span; rebuild the admissible prefix at VM changes."""
from pathlib import Path
import re,runpy,sys
p=Path(__file__).parent
def bounds():
 s=Path('build/switch-runtime/core-perf/opening-stack-window/budget.log').read_text()
 assert 'verified 120 original demo frames' in s
 def get(f):
  pages={int(i):tuple(map(int,(a,b,c,d))) for i,a,b,c,d in re.findall(r'^\[SW_PAGE\] '+str(f)+r' (\d+) (\d+) (\d+) (\d+) (\d+)$',s,re.M)}
  full={int(i):int(h) for i,h in re.findall(r'^\[SW_FULL\] '+str(f)+r' (\d+) (\d+)$',s,re.M)}
  assert set(full)==set(range(128));return pages,full
 pages,full=get(30)
 def count(pg,i):return sum(pg.get(i,(0,0))[:2])
 runs=[];start=None
 for i in range(129):
  if full.get(i)==30:
   if start is None:start=i
  elif start is not None:runs.append((sum(count(pages,j) for j in range(start,i)),start,i));start=None
 _,lo,hi=max(runs)
 pg,m=get(120);end=lo
 while end<hi and m[end]==90:end+=1
 frac=sum(count(pg,j) for j in range(lo,end))/sum(map(sum,pg.values()))
 print('trained pages',lo,hi,'late coverage proxy',frac,flush=True)
 if frac<0.70:raise SystemExit('below offline coverage gate')
 return (0x1180+lo)*4096,(0x1180+hi)*4096
def vm(s):
 lo,hi=bounds();k='uint32_t opening_end4[1u<<20];';assert s.count(k)==1
 s=s.replace(k,k+f'''
__attribute__((visibility("hidden"))) uint32_t sw_limit_words;
static void sw_refresh(void){{
 unsigned va={lo}u;while(va<{hi}u && opening_end4[va>>12]==va+4093u)va+=4096;
 sw_limit_words=(va-{lo}u)>>2;
}}
''')
 k='    memset(opening_end4,0,sizeof opening_end4);';assert s.count(k)==1
 s=s.replace(k,'    sw_limit_words=0;\n'+k)
 cut=s.index('uint32_t ngb_vm_query')
 assert s[:cut].count('    *base = ')==2
 return s[:cut].replace('    *base = ','    sw_refresh();\n    *base = ')+s[cut:]
def transform(s,u):
 lo,hi=bounds();k='#include "recomp_funcs.h"';assert s.count(k)==1
 return s.replace(k,k+f'''
extern __attribute__((visibility("hidden"))) uint32_t sw_limit_words;
static inline __attribute__((always_inline)) uintptr_t sw_addr(uint32_t va){{
 uint32_t d=va-{lo}u;
 if(__builtin_expect(((d>>2)|(d<<30))<sw_limit_words,1))return (uintptr_t)ngb_fast_ram+va;
 return ngb_guest_scalar(va,4);
}}
#undef PUSH32
#define PUSH32(sp,val) do {{uint32_t _pv=(uint32_t)(val);(sp)-=4;*(volatile uint32_t*)sw_addr(sp)=_pv;}} while(0)
#undef POP32
#define POP32(sp,dst) do {{(dst)=*(volatile uint32_t*)sw_addr(sp);(sp)+=4;}} while(0)
''')
if __name__=='__main__':
 if '--test' in sys.argv:
  lo=0x1185000
  for pages in (0,1,5,128):
   for v in (*range(lo-8,lo+pages*4096+8),0,0xffffffff,0x81185000):
    d=(v-lo)&0xffffffff
    assert (((d>>2)|(d<<30)&0xffffffff)<1024*pages)==(lo<=v<lo+4096*pages and v%4==0)
  print('range/alignment predicate agrees at all byte offsets and wraparound probes')
 elif '--select' in sys.argv:bounds()
 else:runpy.run_path(str(p/'model-copy.py'))['build']('stack-prefix',[(True,[2,10,16,26,39])],transform)
