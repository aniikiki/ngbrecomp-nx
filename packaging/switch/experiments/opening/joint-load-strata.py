"""Stratify the buffered same-geometry cohort by draw count before inspecting CPU time."""
from pathlib import Path
from statistics import mean, median
from math import ceil

d=Path('build/switch-runtime/core-perf/opening-present-combined')
def load(arm):
    s=(d/f'jointbuf-{arm}.log').read_text()
    assert 'reason=verified 120 original demo frames' in s
    assert s.index('[WIDE] moving Vulkan scanouts=') < s.index('[PRESENT_MIX]')
    rows=[line.split()[1:] for line in s.splitlines() if line.startswith('[PRESENT_MIX] ')]
    assert len(rows)==120
    return rows

cohort=[]
for group in zip(*(load(a) for a in ('base-1','next-1','base-2','next-2'))):
    a,b,c,e=group
    if not all(x[:5]==a[:5] for x in group): continue
    start,end,draws=map(int,a[:3])
    if not (31<=end<120 and start+1==end): continue
    cohort.append((end,draws,(int(a[5])-int(b[5]))/1e6,(int(c[5])-int(e[5]))/1e6))
assert [x[0] for x in cohort]==list(range(31,120))
# Tie at the median stays in the lower group; group membership never depends on time.
cut=median(x[1] for x in cohort)
for label,rows in [('lower',[x for x in cohort if x[1]<=cut]),('higher',[x for x in cohort if x[1]>cut])]:
    print(label, 'intervals',len(rows),'draw range',min(x[1] for x in rows),max(x[1] for x in rows),
          'both faster',sum(min(x[2:])>0 for x in rows),'mean CPU savings',
          *(round(mean(x[i] for x in rows),4) for i in (2,3)))
for i in (2,3):
    vals=sorted(x[i] for x in cohort); n=ceil(len(vals)/10)
    print('pair',i-1,'median',round(median(vals),4),'mean after removing largest gains',
          round(mean(vals[:-n]),4),'removed intervals',n)
