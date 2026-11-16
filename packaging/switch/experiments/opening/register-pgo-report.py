"""Summarize separate complete opening runs in ABBA order, not 120 independent experiments."""
from pathlib import Path
import re,sys
from statistics import mean,median
pairs=[]
for path in map(Path,sys.argv[1:]):
 s=path.read_text()
 assert '[RESULT] status=1 reason=verified 120 original demo frames' in s,path
 rows=[tuple(map(int,v)) for v in re.findall(r'^\[PGFRAME\] (\d+) (\d+) (\d+) (\d+)$',s,re.M)]
 assert [r[0] for r in rows]==list(range(1,121)) and sum(r[1] for r in rows)==rows[-1][3],path
 v=rows[-1][3]/120e6;pairs.append(v)
 print(path.stem,'ms/frame',round(v,3),'31..120',round(mean(r[1] for r in rows[30:])/1e6,3),'median',round(median(r[1] for r in rows)/1e6,3),'draws',sum(r[2] for r in rows))
if len(pairs)==4:
 a,b,c,d=pairs;print('AB and BA savings ms/frame',round(a-b,3),round(d-c,3),'mean',round((a+d-b-c)/2,3))
