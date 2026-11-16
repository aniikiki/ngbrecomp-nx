"""Specialize optimization level only on opening-hot guest routines. Cold code
keeps its existing layout and ABI flags; no reassociation or fast math."""
from pathlib import Path
import re,os,collections,sys
root=Path.cwd();base=root/'build/switch-runtime';abi=root/'packaging/switch/arm-registers'
d=base/'core-perf/opening-speed';d.mkdir(exist_ok=True);counts=collections.Counter()
for f,ls in re.findall(r'^\[ENTRY_MIX\] (\d+) (.*)$',(base/'core-perf/opening-setup/entry-mix.log').read_text(),re.M):
 if 31<=int(f)<=120:
  for va,n in re.findall(r'([0-9a-f]+):(\d+)',ls):counts[int(va,16)]+=int(n)
n=0
for u in (0,1,2,3,9,10,11,14,16,27,28,29,37,44):
 name=f'recomp_{u:04}.c';s=(base/'gen'/name).read_text()
 def level(m):
  global n
  if counts[int(m[1],16)]<1800:return m[0]
  n+=1;return '__attribute__((optimize("O3","no-optimize-sibling-calls","no-ipa-ra","no-fast-math","fp-contract=off"))) '+m[0]
 s=re.sub(r'^void (?:sub_|d3d_orig_)([0-9A-F]+)\(void\)$',level,s,flags=re.M)
 if '--scan' not in sys.argv:(d/name).write_text(s)
print('hot definitions annotated',n,flush=True)
if '--scan' in sys.argv:sys.exit()
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text();k=' sp.run(c,cwd=w,check=True)';assert s.count(k)==1
s=s.replace(k,' c[-1]=str(o/n)\n'+k)
exec(compile(s,'speed-abi','exec'),{})
exec(compile((abi/'gates.py').read_text(),'speed-gates','exec'),{})
for pat in ('recomp_*.s','recomp_*.c'):
 for f in d.glob(pat):f.unlink()
