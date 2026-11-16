from pathlib import Path
import re, runpy
targets=(*runpy.run_path(str(Path(__file__).with_name('script-arm-cost.py')))['targets'],0)
s=Path('build/switch-runtime/core-perf/opening-script-arm-cost/budget.log').read_text()
assert 'verified 120 original demo frames' in s
for f,nframes in [(30,30),(120,90)]:
 rows=[tuple(map(int,r)) for r in re.findall(r'^\[TREE_COST\] '+str(f)+r' (\d+) calls=(\d+) samples=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+) cross=(\d+)',s,re.M)]
 assert len(rows)==20 and rows[-1]==(19,0,0,0,0,0,0) and sum(r[1] for r in rows)>0
 rank=[]
 for i,c,n,t,b,z,x in rows[:-1]:
    if c and min(n,b)>=10 and not x:rank.append(((t/n-z/b)*c/1000/nframes,i,c,n,b))
    elif c:print('low coverage',f,hex(targets[i]),c,n,b,x)
 print('window',f,'calls',sum(r[1] for r in rows),'top arms (us per host frame, target, calls, real/blank)')
 for us,i,c,n,b in sorted(rank,reverse=True)[:6]:print(round(us,2),hex(targets[i]),c,n,b)
