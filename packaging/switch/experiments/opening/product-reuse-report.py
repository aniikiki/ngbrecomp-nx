"""Exact input matches for one bounded address-pair table, not a speedup."""
import re
from pathlib import Path
p=Path('build/switch-runtime/core-perf/opening-product-reuse/distribution.log')
s=p.read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
rows=re.findall(r'^\[PRODUCT_REUSE\] (.*)$',s,re.M)
assert len(rows)==2
for expected,line in zip((30,120),rows):
 end,n,readable,pair,left,right,both,within,caller,collision=map(int,line.split())
 assert end==expected and 0<=within<=both<=min(left,right)<=max(left,right)<=pair<=readable<=n and caller<=both and collision<=readable-pair
 print(f'through {end}: {both}/{n} ({both/n:.1%}) exact source bytes; {within} same flip, {both-within} earlier flip; {n-readable} unreadable, {collision} conflicting keys')
