"""Only spend eight timing runs if this new transform actually removes many
checks in the measured steady window. This is a screening rule, not a speedup."""
from pathlib import Path
import re,sys
p=Path('build/switch-runtime/core-perf/opening-span-audit/distribution.log')
s=p.read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
rows=[tuple(map(int,m)) for m in re.findall(r'^\[SPAN_COUNT\] (\d+) (\d+) (\d+)$',s,re.M)]
assert [f for f,_,_ in rows]==[30,120]
for (f,g,o),n in zip(rows,(30,90)):
 assert 2*g<=o
 print(f,'checks replaced per frame',(o-g)/n,'original ops per frame',o/n)
# Previous stack-groups already eliminated ~57k guest checks/frame in the
# opening with no whole-frame benefit. Do not rerun a weaker coverage bet.
if (rows[1][2]-rows[1][1])/90 < 57000:
 print('below previous no-gain coverage; skip full ABBA');sys.exit(3)
