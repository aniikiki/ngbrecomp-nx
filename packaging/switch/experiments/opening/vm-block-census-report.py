"""Real eligibility among guard executions; this is not a timing run."""
from pathlib import Path
import re
d=Path("build/switch-runtime/core-perf/opening-vm-block-census")
s=(d/"budget.log").read_text()
assert "[RESULT] status=1 reason=verified 120 original demo frames" in s
rows=re.findall(r"^\[VB_CENSUS\] (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$",s,re.M)
assert [int(row[0]) for row in rows]==[30,120]
for f,*bins in rows:
 h,partial,edge,out,alias=map(int,bins);total=h+partial+edge+out+alias
 print(f,"checks",total,"accepted",h,"fraction",round(h/total,4),"partial",partial,"edge",edge,"outside low",out,"outside high",alias)
