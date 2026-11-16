"""Observe (and optionally fix in replay only) the input to the game's CRT seed setter."""
from pathlib import Path
import runpy
def transform(s,u):
 for va,needle,change in [
  ('0036E134','MEM32(eax + 0x14) = ecx;', 'rr_set(ecx); MEM32(eax + 0x14) = rr_fixed ? 1u : ecx;'),
  ('0036E141','eax = eax & 0x7FFF;', 'eax = eax & 0x7FFF; rr_observe(eax);')]:
  a=s.index('void sub_'+va+'(void)\n{');b=s.index('\n}',a)
  assert s[a:b].count(needle)==1
  s=s[:a]+s[a:b].replace(needle,change)+s[b:]
 return 'extern unsigned rr_fixed;extern void rr_set(unsigned),rr_observe(unsigned);\n'+s
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('rng-correspondence',[(False,[37])],transform)
