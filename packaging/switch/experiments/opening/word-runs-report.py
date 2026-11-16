from collections import Counter
from pathlib import Path
import re
d=Path('build/switch-runtime/core-perf/opening-word-runs')
s=(d/'budget.log').read_text();assert 'reason=verified 120 original demo frames' in s
sites={}
for l in (d/'sites.txt').read_text().splitlines():
 u,i,prev,fn,stmts=l.split(maxsplit=4);sites[int(u),int(i)]=(fn,stmts)
rows=[tuple(map(int,r)) for r in re.findall(r'^\[WORD_RUN\] (\d+) (\d+) (\d+) (\d+)$',s,re.M)]
assert [r[0] for r in rows]==[0,1]
for k,all_,page,hit in rows:
 n=(30,90)[k]; assert 0<=hit<=page<=all_
 print(f'{n} frames: observed {all_}, consecutive ordinary same-page {page}, whitelisted {hit}; per frame {hit/n:.1f}, fraction of observed {hit/all_:.2%}')
hits=Counter();ops=Counter();bases=Counter()
for u,i,n in re.findall(r'^\[WORD_PAIR\] (\d+) (\d+) (\d+)$',s,re.M):
 fn,stmts=sites[int(u),int(i)];bases[re.search(r"MEM32\((\w+)",stmts)[1]]+=int(n);hits[fn]+=int(n);ops[fn,stmts]+=int(n)
assert sum(hits.values())==rows[-1][-1]
print("base register, late window",bases.most_common())
for (fn,stmts),n in ops.most_common(10): print(fn,round(n/90,1),stmts)
