"""Count current guest stack page matches only in sampled private guest bodies."""
from collections import Counter
from pathlib import Path
import bisect,re,sys
d=Path('build/switch-runtime/core-perf/opening-stack-distance')
symbols={}
for line in (d/'symbols.txt').read_text().splitlines():
    a,n,_,name=line.split(maxsplit=3);a,n=int(a,16),int(n,16)
    if n>symbols.get(a,(0,''))[0]:symbols[a]=(n,name)
keys=sorted(symbols)
for i in (list(map(int,sys.argv[1:])) or range(1,5)):
    s=(d/f'run-{i}.log').read_text()
    assert 'reason=verified 120 original demo frames' in s
    for lo,hi in ((1,30),(31,120)):
        counts=Counter();same=Counter()
        for f,pc,page,stack in re.findall(r'^\[STACK_DISTANCE\] (\d+) (\w+) (\w+) (\w+)$',s,re.M):
            if not lo<=int(f)<=hi:continue
            pc,page,stack=(int(x,16) for x in (pc,page,stack))
            j=bisect.bisect_right(keys,pc)-1
            if j<0:continue
            start=keys[j];size,name=symbols[start]
            if pc>=start+size or not name.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):continue
            cat='same' if page==stack else 'neighbor' if abs(page-stack)==1 else 'other'
            counts[cat]+=1
            if cat=='same':same[name]+=1
        print(i,lo,hi,dict(counts),'distinct bodies on same page',len(same),same.most_common(3))
