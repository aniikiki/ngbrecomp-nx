"""How often was an interrupted guest PC even inside one of the transformed functions?"""
import bisect,collections,re,runpy
from pathlib import Path
p=Path(__file__).parent
q=runpy.run_path(str(p/'rmw-flags.py'))
root=Path('build/switch-runtime'); d=root/'core-perf/opening-compact-profile'
owners={}
for unit in q['units']:
 src=(root/'gen'/f'recomp_{unit:04}.c').read_text()
 for n,body in re.findall(r'^void (\w+)\(void\)\n\{(.*?)^\}',src,re.M|re.S):
  cnt=len(q['pat'].findall(body))
  if cnt:owners[n]=cnt
sym={}
for row in (d/'symbols.txt').read_text().splitlines():
 a,n,_,name=row.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sym.get(a,(0,None))[0]:sym[a]=n,name
keys=sorted(sym)
print('owners',len(owners),'sites',sum(owners.values()))
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text();assert 'verified 120 original demo frames' in s
 hits=collections.Counter();total=0
 for f,p in re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M):
  if not 31<=int(f)<=120:continue
  total+=1;pc=int(p,16);j=bisect.bisect_right(keys,pc)-1
  if j<0:continue
  a=keys[j];size,n=sym[a];fn=n.removeprefix('ngb_reg_').split('.')[0]
  if pc<a+size and fn in owners:hits[fn]+=1
 print(i,sum(hits.values()),'/',total,hits.most_common(4))
