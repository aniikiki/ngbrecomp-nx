"""Counterfactual fixed saving; benchmark baseline only. No extrapolation from host."""
from pathlib import Path
import re, statistics as st
from math import ceil
path,=Path('build/switch-runtime/device-logs').glob('0.55.0-wide-*/boot.log')
s=path.read_text()
assert re.findall(r'\[CLOCK\] first=(\d+) cpu_hz=(\d+) gpu_hz=(\d+)',s)[:2]==[('1','1785000000','307200000'),('121','1785000000','307200000')]
w=[tuple(map(int,x)) for x in re.findall(r'window frames=(\d+) ms=(\d+) over_16.67ms=(\d+) p95_us=(\d+)',s)[:2]]
assert [x[0] for x in w]==[30,90]
r=[(int(f),int(c)/19200,int(d)/19200,int(n)) for f,n,d,c in re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=(\d+) ticks=(\d+) cpu=(\d+) rc=0',s)]
assert [x[0] for x in r]==list(range(31,121))
budget=1000/60
for lo,hi in ((31,60),(61,90),(91,120),(31,120)):
 a=[cpu for f,cpu,*_ in r if lo<=f<=hi];b=[max(cpu-5-budget,0) for cpu in a]
 print(lo,hi,'mean / p95 CPU',round(st.mean(a),3),round(sorted(a)[ceil(.95*len(a))-1],3),'over CPU budget after 5ms',sum(x>0 for x in b),'residual positive excess ms',round(sum(b),3))
print('residual frames',[(f,round(c-5-budget,2)) for f,c,*_ in r if c-5>budget])
for n,ms,late,p95 in w:
 k=n-((95*n-1)//100)
 print('window',n,'at least',k,'wall intervals >=',p95/1000,'ms; minimum summed residual excess on these after 5ms',round(k*max(0,p95/1000-5-budget),3))
elapsed=int(re.search(r'3D scene flips=120 draws=\d+ elapsed_ms=(\d+)',s)[1]);print('ideal remaining wall time if each flip saves 5 ms (rounding ~1 ms)',elapsed-120*5)
