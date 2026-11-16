"""Rank dynamically hit guards, not fallback paths or CPU milliseconds."""
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text();assert 'verified 120 original demo frames' in s
for f,frames in [(30,30),(120,90)]:
 h,c=map(int,re.search(r'^\[MIXED_HIT\] '+str(f)+r' (\d+) (\d+)$',s,re.M).groups())
 rows=[(a,int(n),int(k)) for a,n,k in re.findall(r'^\[MIXED_OWNER\] '+str(f)+r' (\w+) (\d+) (\d+)$',s,re.M)]
 assert sum(n for _,n,_ in rows)==h and sum(k for _,_,k in rows)==c
 print(f,'active owners',len(rows),'groups/frame',round(h/frames,2),'redundant source checks/frame',round(c/frames,2),'top five:',[(a,round(k/frames,2)) for a,n,k in sorted(rows,key=lambda x:-x[2])[:5]])
