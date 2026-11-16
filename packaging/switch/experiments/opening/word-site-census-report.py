from pathlib import Path
import re,sys
exact="--word-address-census" in sys.argv
tag="word-address-census" if exact else "word-site-census"
s=Path(f'build/switch-runtime/core-perf/opening-{tag}/budget.log').read_text()
assert 'verified 120 original demo frames' in s
rows=[(int(u),int(i),int(n),int(pg,16),int(v),int(l),int(h)) for u,i,n,pg,v,l,h in re.findall(r'^\[WS_SITE\] (\d+) (\d+) (\d+) (\w+) (\d+) (\d+) (\d+)$',s,re.M)]
assert rows and len({r[:2] for r in rows})==len(rows) and all(v<=n and h<=l for _,_,n,_,v,l,h in rows)
total=sum(r[5] for r in rows)
# Select only from training. VM/alias predictions need separate live validity; image-only membership below.
selected=[r for r in rows if r[2]>=30 and 4*r[4]>=3*r[2]]
for label,group in [('all predictions',rows),('training-filtered predictions',selected),('filtered image pages',[r for r in selected if 8<=(r[3]>>12 if exact else r[3])<4096])]:
 hits=sum(r[6] for r in group);attempt=sum(r[5] for r in group)
 print(label,len(group),'sites;',round(attempt/90),'attempts/frame;',round(hits/90),'matches/frame;',round(hits/total*100,2),'% of measured dynamic word references')
