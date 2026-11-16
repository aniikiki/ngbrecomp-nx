"""Screen opening candidates against the actual 1785 MHz budget. This is a
host-side heuristic, not hardware verification. Retain the non-CPU
gap from the hardware baseline; never add gains from separate candidates."""
import re,sys
from pathlib import Path
from statistics import mean
d=Path('build/switch-runtime/core-perf/wide-start')
base=next(Path('build/switch-runtime/device-logs').glob('0.55.0-wide-*/boot.log')).read_text()
cl=re.search(r'\[CLOCK\] first=1 cpu_hz=(\d+) gpu_hz=(\d+)',base)
def window(f):
 return int(re.search(r'3D scene flips='+str(f)+r' draws=\d+ elapsed_ms=(\d+)',base)[1])
assert cl and tuple(map(int,cl.groups()))==(1785000000,307200000)
print(f'Hardware scene start to flip 120: {window(120)/120:.3f} ms per flip including startup ({window(120)} ms total; 60 Hz budget 2000 ms).')
wall=(window(120)-window(30))/90
cpu_rows=re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=\d+ ticks=\d+ cpu=(\d+) rc=0',base)[:90]
assert [int(f) for f,n in cpu_rows]==list(range(31,121))
cpu=mean(int(n) for _,n in cpu_rows)/19200
required=(wall-1000/60)/cpu
print(f'Hardware baseline: {wall:.3f} ms wall, {cpu:.3f} ms game CPU; required game CPU saving with other time unchanged: {required:.2%}.')
print(f'Hardware split: first 30 wall {window(30)/30:.3f} ms/flip, excess {window(30)-500} ms; next 90 excess {window(120)-window(30)-1500} ms.')

for tag in sys.argv[1:]:
 ratios=[];starts=[];all_frames=[]
 for i in range(1,5):
  both=[]
  for arm in ('original','limit'):
   p=d/f'{tag}-{arm}-{i}.log'
   if not p.exists():break
   s=p.read_text()
   if '[RESULT] status=1 reason=verified 120 original demo frames' not in s:break
   rr=re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)
   assert [int(f) for f,_,_ in rr]==list(range(1,121))
   both.append([mean(int(n) for _,n,_ in window_rows) for window_rows in (rr[:30],rr[30:],rr)])
  if len(both)==2:
   for j,group in enumerate((starts,ratios,all_frames)):group.append(1-both[1][j]/both[0][j])
 print(tag,len(ratios),'complete pairs;', 'host thread savings 1..30 / 31..120 / 1..120: '+ ' / '.join(f'{mean(x):.2%}' for x in (starts,ratios,all_frames)) if ratios else 'pending',
       'clears sustained-only host heuristic; startup and hardware unverified' if len(ratios)==4 and min(ratios)>=required else 'host evidence insufficient')
