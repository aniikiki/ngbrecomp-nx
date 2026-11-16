from pathlib import Path
import re
d=Path('build/switch-runtime')
import sys
log=(d/'core-perf'/('opening-mesh-common-cost' if '--common' in sys.argv else 'opening-mesh-expensive-cost' if '--expensive' in sys.argv else 'opening-mesh-cost')/'budget.log').read_text()
assert 'verified 120 original demo frames' in log
s=(d/'gen/recomp_0028.c').read_text().split('void sub_0030BCA0(void)\n{')[1].split('\n}')[0]
sites=re.findall(r'PUSH32\(esp, 0x(\w+)u\); RECOMP_(?:ABI_CALL\(0x(\w+)u|ICALL_SAFE_AT\()',s)
rows=[tuple(map(int,r)) for r in re.findall(r'^\[TREE_COST\] (\d+) (\d+) calls=(\d+) samples=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+) cross=(\d+)$',log,re.M)]
assert len(sites)==18 and [(r[0],r[1]) for r in rows]==[(f,i) for f in (30,120) for i in range(18)]
for f,i,c,n,t,b,z,x in rows:
 if c:print(f,*sites[i],round(c/(30 if f==30 else 90),2),'calls/frame',round((t/n-z/b)*c/(30 if f==30 else 90)*1e-6,5) if n and b and not x else None,'ms/frame')
