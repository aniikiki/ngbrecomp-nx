"""Specialize only the seven measured 16-DWORD model copies, leaving the generated fallback intact."""
from pathlib import Path
import runpy,sys
sites={16:['001CBD00','001D7810'],28:['003078B0','00307B80','00307A10','0030C160'],29:['00317D10']}
old='if (!g_df) { uint32_t _n = ecx * 4;'
fast='''if(ecx==16 && !g_df && esi>=4096u && edi>=4096u &&
      esi<NGB_RAM_BYTES && edi<NGB_RAM_BYTES &&
      (esi&4095u)+64<=ngb_fast_page_bytes[esi>>12] &&
      (edi&4095u)+64<=ngb_fast_page_bytes[edi>>12] &&
      (esi+64<=edi || edi+64<=esi)){
      memcpy(ngb_fast_ram+edi,ngb_fast_ram+esi,64);esi+=64;edi+=64;
    } else '''
def transform(s,unit):
 for va in sites[unit]:
  a=s.index('void sub_'+va+'(void)\n{');b=s.index('\n}',a);body=s[a:b]
  assert body.count(old)==body.count('/* rep movsd */')==1
  s=s[:a]+body.replace(old,fast+old)+s[b:]
 return s
def build(tag, groups, transform):
 p=Path(__file__).parent;root=Path('build/switch-runtime')
 for compact,units in groups:
  s=(p/'page-hot-o3.py').read_text()
  a=s.index('next_set=');b=s.index('parent=d.parent',a)
  s=s[:a]+"""compact=USE_COMPACT
cold_scalar=size_hot=simple_layout=page_bias=loop_ira=block_predicate=effective_mask=False
d=(base/'core-perf/opening-model-copy').resolve();d.mkdir(exist_ok=True)
"""+s[b:]
  a=s.index('names=');b=s.index('\ns=s[:s.index',a)
  s=s[:a]+"""names=[f'recomp_{i:04}.c' for i in UNITS]
for n,i in zip(names,UNITS):(d/n).write_text(transform((base/'gen'/n).read_text(),i))
"""+s[b:]
  if not compact:
   a=s.index('s=s.replace(k," c[-1:');b=s.index('exec(compile',a);s=s[:a]+s[b:]
  k="exec(compile(s,'page-o3','exec'),{})"
  s=s.replace(k,"s=s.replace(k,\" c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n\"+k)\n"+k)
  exec(compile(s.replace('opening-model-copy','opening-'+tag),tag,'exec'),{'USE_COMPACT':compact,'UNITS':units,'transform':transform})
  for i in units:(root/f'core-perf/opening-{tag}/recomp_{i:04}.c').unlink()

if __name__=='__main__':build('model-copy',[(True,[16]),(False,[28,29])],transform)
