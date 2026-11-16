"""Same-seed original vs split, retain distinct present CPU and epoch-to-flip wall denominators."""
from pathlib import Path
from statistics import mean
import re,sys
ps_range="--ps-range" in sys.argv
root=Path('build/switch-runtime');d=root/'core-perf/opening-rng-correspondence'
def elapsed(text):
 rows=re.findall(r'3D scene flips=(30|120) draws=(\d+) elapsed_ms=(\d+)',text)
 assert [int(f) for f,_,_ in rows]==[30,120]
 a,b=[int(t) for f,n,t in rows];return a/30,(b-a)/90,b/120
for i in [1,2]:
 results=[]
 for arm in (['psr-control','psr-trial'] if ps_range else ['original','split']):
  t=(d/f'{"holdout" if ps_range else "cumulative-one"}-{arm}-{i}.log').read_text()
  assert 'reason=verified 120 original demo frames' in t
  rows=[v for l in t.splitlines() if (v:=l.split())[:1]==['[PRESENT_MIX]'] and int(v[1])+1==int(v[2]) and 1<=int(v[2])<=119]
  assert [int(v[2]) for v in rows]==list(range(1,120))
  rng={int(v[1]):v[-2:] for l in t.splitlines() if (v:=l.split())[:1]==['[RNG_PRESENT]'] and v[2]=='1'}
  sig=[(v[3:6],rng[int(v[2])]) for v in rows]
  cpu=[mean(int(v[6])/1e6 for v in block) for block in (rows[:30],rows[30:],rows)]
  results.append((sig,cpu,elapsed(t),[int(v[6])/1e6 for v in rows]))
 a,b=results
 print('pair',i,'matching geometry/RNG:',sum(x==y for x,y in zip(a[0],b[0])),'/119')
 if ps_range:
  diffs=[a[3][j]-b[3][j] for j in range(30,119) if a[0][j]==b[0][j]]
  print('matched late intervals',len(diffs),'mean CPU saving ms',round(mean(diffs),4) if diffs else None)
 for what,base,trial in [('host game thread',a[1],b[1]),('host elapsed',a[2],b[2])]:
  print(what,'ms/frame early,late,all; baseline',*[round(x,4) for x in base],'candidate',*[round(x,4) for x in trial],'saved',*[round(x-y,4) for x,y in zip(base,trial)])
log,=list((root/'device-logs').glob('0.55.0-wide-*/boot.log'))
print('historical device (epoch to 30, 30 to 120, epoch to 120) ms/frame:',elapsed(log.read_text()))
