"""Source comparison ranks describe traffic only: GCC may generate a different decision tree."""
from pathlib import Path
import re,runpy,collections
p=Path(__file__).parent
pat=runpy.run_path(str(p/'jump-buckets.py'))['pat']
tables={}
for unit in (0,2):
 for m in pat.finditer(Path(f'build/switch-runtime/gen/recomp_{unit:04}.c').read_text()):
  if int(m[2])<16:continue
  table=int(re.search(r'\+ (0x[0-9A-F]+)\); /\* switch:',m['header'])[1],16)
  targets=[int(a,16) for a in re.findall(r'if \(_jt == 0x([0-9A-F]+)u\)',m['arms'])]
  if table in tables:assert targets==tables[table]
  tables[table]=targets
s=Path('build/switch-runtime/core-perf/opening-target-hist/budget.log').read_text()
assert 'verified 120 original demo frames' in s
for end,frames in [(30,30),(120,90)]:
 rows=collections.defaultdict(collections.Counter)
 for phase,table,va,hits in re.findall(r'^\[TARGET_HIST\] (\d+) (\w+) (\w+) (\d+)$',s,re.M):
  if int(phase)==end:
   a,v=int(table,16),int(va,16);assert a in tables and v not in rows[a]
   rows[a][v]=int(hits)
 assert rows
 print('window end',end,'active tables',len(rows),'dispatches/frame',round(sum(c.total() for c in rows.values())/frames,2))
 for a,c in sorted(rows.items(),key=lambda kv:-kv[1].total()):
  v,n=c.most_common(1)[0]; arms=tables[a];rank=arms.index(v)+1 if v in arms else None
  print(hex(a),'calls/frame',round(c.total()/frames,1),'top',hex(v),round(n/c.total(),3),'source rank',rank,'fallback hits',sum(k for t,k in c.items() if t not in arms))
