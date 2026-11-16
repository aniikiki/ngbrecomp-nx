"""Train on the first 30 frames; check target identity and recurrence separately on 31..120."""
from pathlib import Path
from collections import Counter,defaultdict
import bisect,re
d=Path('build/switch-runtime/core-perf/opening-gate-pairs')
s=(d/'budget.log').read_text();assert 'reason=verified 120 original demo frames' in s
names={};starts={}
for l in (d/'symbols.txt').read_text().splitlines():
 a,n,_,fn=l.split(maxsplit=3);a,n=int(a,16),int(n,16)
 names.setdefault(a,set()).add(fn)
 if n>starts.get(a,(0,''))[0]:starts[a]=n,fn
keys=sorted(starts)
entry=Path('build/switch-runtime/core-perf/opening-full-page/entry.S').read_text()
wrappers=set(re.findall(r'^\.global (\w+)$',entry,re.M))
rows=defaultdict(lambda:defaultdict(Counter))
for f,p,t,n in re.findall(r'^\[GP\] (\d+) (\w+) (\w+) (\d+)$',s,re.M):
 rows[int(f)][int(p,16)][int(t,16)]+=int(n)
trained={}
for pc,c in rows[30].items():
 t,n=c.most_common(1)[0]
 if n>=30 and n/sum(c.values())>=.95 and names.get(t,set())&wrappers:trained[pc]=t
for f,r in rows.items():
 total=sum(sum(c.values()) for c in r.values());assert f'[GP_TOTAL] {f} {total}\n' in s
 matched=sum(c[trained[p]] for p,c in r.items() if p in trained)
 eligible=sum(n for c in r.values() for t,n in c.items() if names.get(t,set())&wrappers)
 print(f,'calls',total,'exact public wrapper targets',eligible,'selected sites',len(trained),'matching calls',matched)
for pc,t in sorted(trained.items(),key=lambda j:-rows[120][j[0]][j[1]])[:10]:
 a=keys[bisect.bisect_right(keys,pc)-1];size,fn=starts[a];assert pc<a+size
 print(fn,hex(pc-a),sorted(names[t]&wrappers),rows[120][pc][t],sum(rows[120][pc].values()))
