"""Summarize input disagreement separately from dependence estimates."""
import re,sys
from pathlib import Path
from collections import Counter
p=Path(sys.argv[1]);s=p.read_text();assert 'verified original combat window' in s
out=[[0,0] for _ in range(6)];frames=Counter();damaged=Counter()
for f,i,data in re.findall(r'^\[ACTOR_INPUT\] (\d+) (\d+)(.*)$',s,re.M):
 cols=[list(map(int,x.split(':'))) for x in data.split()];assert len(cols)==6
 frames[int(f)]+=1
 for j,(diff,n) in enumerate(cols):
  assert diff<=n;out[j][0]+=diff;out[j][1]+=n;damaged[j]+=bool(diff)
assert set(frames)==set(range(1801,1813)) and min(frames.values())>0
for i,k in enumerate(['stack','matrix+cursor','two collision fields','actor pool','dynamic RAM','other static']):
 print(k,'different/read bytes',*out[i], 'affected iterations',damaged[i],'of',sum(frames.values()))
pages=Counter()
for f,a,n in re.findall(r'^\[INPUT_PAGE\] (\d+) (\w+) (\d+)$',s,re.M):pages[a]+=int(n)
print('top among per-frame top four',pages.most_common(12))
