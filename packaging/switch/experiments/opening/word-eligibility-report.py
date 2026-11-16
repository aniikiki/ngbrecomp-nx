from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-word-eligibility/budget.log').read_text()
assert 'verified 120 original demo frames' in s
r=[tuple(map(int,l.split())) for l in re.findall(r'^\[WE_SITE\] (.*)$',s,re.M)]
assert r and len({v[:2] for v in r})==len(r)
for lo in (2,6):
 n,exceptions,cross,high=[sum(v[i] for v in r) for i in range(lo,lo+4)]
 pages=[(int(p,16),int(a if lo==2 else b)) for p,a,b in re.findall(r'^\[WE_PAGE\] (\w+) (\d+) (\d+)$',s,re.M)]
 assert sum(v for p,v in pages)==exceptions
 print('window',lo,'dynamic words',n,'fallback',exceptions,'cross',cross,'high',high,'leading fallback pages',sorted(pages,key=lambda p:-p[1])[:6])
for minimum in (1,30,300):
 selected=[v for v in r if v[2]>=minimum and v[3]==0]
 print('trained ordinary sites min',minimum,'held out accesses',sum(v[6] for v in selected),'fallback',sum(v[7] for v in selected),'sites now requiring fallback',sum(v[7]>0 for v in selected))
