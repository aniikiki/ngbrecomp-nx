"""Resolve public entry counters for each phase; ignore private direct calls."""
from pathlib import Path
import re,collections
d=Path('build/switch-runtime/core-perf/opening-public-entry')
names=(d/'public-names.txt').read_text().splitlines()
s=(d/'budget.log').read_text();assert 'reason=verified 120 original demo frames' in s
for f in (30,120):
 c=collections.Counter()
 for i,n in re.findall(r'^\[PUBLIC_ENTRY\] '+str(f)+r' (\d+) (\d+)$',s,re.M):
  name=names[int(i)];assert name not in c;c[name]=int(n)
 print(f,'total',c.total(),'unique',len(c),'top',c.most_common(8))
