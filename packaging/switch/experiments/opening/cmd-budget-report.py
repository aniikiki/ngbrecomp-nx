"""Describe estimated inclusive host CPU budget, never a projected console saving."""
import re,sys
from pathlib import Path
s=Path(sys.argv[1]).read_text()
assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
rows=[tuple(map(int,m)) for m in re.findall(r'^\[CMD_BUDGET\] (\d+) (\d+) (\d+) (\d+)$',s,re.M)]
frames=[tuple(map(int,m)) for m in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) \d+$',s,re.M)]
assert [r[0] for r in rows]==[30,120] and [r[0] for r in frames]==list(range(1,121))
first=1
for last,entries,samples,ns in rows:
    assert 0<samples<=(entries+6)//7
    estimate=ns*entries/samples
    total=sum(x for i,x in frames if first<=i<=last)
    print(f'{first}..{last}: {samples}/{entries} sampled; {estimate/(last-first+1)/1e6:.4f} ms/frame estimated inclusive, {estimate/total:.2%} of instrumented guest CPU')
    first=last+1
