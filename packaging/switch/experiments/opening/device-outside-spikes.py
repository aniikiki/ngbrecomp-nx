"""Remove the worst intervals, not just a hypothetical fixed cost per frame."""
import re,statistics as st
from pathlib import Path
p,=Path('build/switch-runtime/device-logs').glob('0.55.0-wide-*/boot.log')
s=p.read_text()
assert re.findall(r'\[CLOCK\] first=(\d+) cpu_hz=(\d+) gpu_hz=(\d+)',s)[:2]==[('1','1785000000','307200000'),('121','1785000000','307200000')]
r=[(int(f),int(n),(int(c)-int(d))/19200,int(c)/19200) for f,n,d,c in re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=(\d+) ticks=(\d+) cpu=(\d+) rc=0',s)]
assert [x[0] for x in r]==list(range(31,121))
budget=1000/60
rows=sorted(r,key=lambda x:-x[2])
ex=lambda x:max(0,x[2]-budget)
print('worst',[(x[0],round(x[2],3)) for x in rows[:5]])
for k in (0,2,5,9):
 a=rows[k:]
 print('omit',k,'mean/median outside',round(st.mean(x[2] for x in a),3),round(st.median(x[2] for x in a),3),'over',sum(ex(x)>0 for x in a),'of',len(a),'remaining positive excess',round(sum(map(ex,a)),2),'ms')
print('split by draws, balanced within each 30-frame phase:')
for group in (0,1):
 a=[]
 for start in (0,30,60):
  win=sorted(r[start:start+30],key=lambda x:(x[1],x[0]))
  a.extend(win[15*group:15*group+15])
 print('draws',round(st.mean(x[1] for x in a),1),'median outside',round(st.median(x[2] for x in a),3),'over',sum(ex(x)>0 for x in a),len(a))
