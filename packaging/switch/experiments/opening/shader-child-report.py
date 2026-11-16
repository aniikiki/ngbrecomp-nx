from pathlib import Path
import re
root=Path('build/switch-runtime')
s=(root/'core-perf/opening-shader-child/budget.log').read_text()
assert 'verified 120 original demo frames' in s
unit=(root/'gen/recomp_0016.c').read_text().split('void sub_001D6E20(void)\n{',1)[1].split('\n}',1)[0]
sites=re.findall(r'PUSH32\(esp, 0x(\w+)u\); RECOMP_ABI_CALL\(0x(\w+)u,',unit)
assert len(sites)==20
for end,nframes in [(30,30),(120,90)]:
 rows=[tuple(map(int,r)) for r in re.findall(r'^\[TREE_COST\] '+str(end)+r' (\d+) calls=(\d+) samples=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+) cross=(\d+)$',s,re.M)]
 assert [r[0] for r in rows]==list(range(20))
 ranked=[]
 for i,c,n,t,b,z,x in rows:
    if c and n and b and not x:
        ranked.append(((t/n-z/b)*c/(1000*nframes),sites[i],c,n,b))
    elif c:
        print('unresolved',end,sites[i],c,n,b,x)
 for us,pair,c,n,b in sorted(ranked,reverse=True): print(end,*pair,c,n,b,round(us,2))
