"""Calibrated, inclusive host setup child times, independently checked against entry counts."""
from pathlib import Path
import re,sys
d=Path('build/switch-runtime')
old=(d/'core-perf/opening-guest-sites/budget.log').read_text()
common='--common' in sys.argv
new=(d/'core-perf'/('opening-mesh-expensive-setup' if '--expensive' in sys.argv else 'opening-mesh-common-setup' if common else 'opening-setup-cost')/'budget.log').read_text()
assert all('verified 120 original demo frames' in l for l in (old,new))
body=(d/'gen/recomp_0028.c').read_text().split('void sub_0030B7E0(void)\n{')[1].split('\n}')[0]
sites=[tuple(int(x,16) for x in pair) for pair in re.findall(r'PUSH32\(esp, 0x(\w+)u\); RECOMP_ABI_CALL\(0x(\w+)u',body)]
assert len(sites)==13
for f,nf in [(30,30),(120,90)]:
    independent={(int(r,16),int(v,16)):int(n) for r,v,n in re.findall(r'^\[GUEST_SITE\] '+str(f)+r' (\w+) (\w+) (\d+)$',old,re.M)}
    rows=[tuple(map(int,r)) for r in re.findall(r'^\[TREE_COST\] '+str(f)+r' (\d+) calls=(\d+) samples=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+) cross=(\d+)$',new,re.M)]
    assert [r[0] for r in rows]==list(range(18)) and not any(any(r[1:]) for r in rows[13:])
    print('phase',f,'return/target, calls(measurement/all-caller census), samples, corrected us/frame')
    for i,c,n,t,b,z,x in rows[:13]:
        if not c:continue
        r,v=sites[i]; print('%x/%x'%(r,v),c,independent.get((r,v),"unobserved"),n,round((t/n-z/b)*c/nf/1000,2) if n and b and not x else None)
