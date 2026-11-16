from pathlib import Path
from statistics import median,mean
import re,random,sys
s=Path(sys.argv[1]).read_text();r=[tuple(map(int,m)) for m in re.findall(r'^\[THREAD_PAIR\] (\d+) (\d+) (\d+)$',s,re.M)]
assert [x[0] for x in r]==list(range(4,68))
assert s.count('diff=0 extra=0 regs=0')==2
a,b=[median(t)/32000 for t in list(zip(*r))[1:]]
diff=[(x-y)/32000 for _,x,y in r];blocks=[mean(diff[i:i+4]) for i in range(0,len(diff),4)]
rng=random.Random(531);boot=sorted(mean(rng.choices(blocks,k=len(blocks))) for _ in range(4000))
print(f'pair p50 serial {a:.2f} us, parallel {b:.2f} us; mean saved {mean(diff):.2f} us [four-pair block interval {boot[99]:.2f}, {boot[3899]:.2f}]; median ratio {a/b:.3f}')
