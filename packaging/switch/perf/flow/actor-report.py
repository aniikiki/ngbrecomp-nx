"""Report the longest inter-actor chains and where a private-scratch oracle still waits."""
from pathlib import Path
from collections import Counter
from bisect import bisect_right
import re,sys
s=Path(sys.argv[1]).read_text()
assert 'verified original combat window' in s
symbols=[]
for line in Path(sys.argv[2]).read_text().splitlines():
 m=re.match(r'^([0-9a-f]+) [tT] (\S+)$',line)
 if m:symbols.append((int(m[1],16),m[2]))
symbols.sort();keys=[n for n,_ in symbols]
def symbol(pc):
 i=bisect_right(keys,int(pc,16))-1
 return symbols[i][1] if i>=0 else '?'
for k in (1,2):
 rows=[list(map(int,r)) for r in re.findall(r'\[ACTOR_PATH\] frame=(\d+) loop='+str(k)+r' calls=(\d+) actors=(\d+) total=(\d+) raw=(\d+) private=(\d+) independent=(\d+)',s)]
 assert [r[0] for r in rows]==list(range(1801,1813)) and all(r[3] for r in rows)
 total,raw,private,ideal=[sum(x) for x in list(zip(*rows))[3:]]
 print(f'loop={k} work={total} strict_RAW={raw} private={private} free={ideal}; shares {raw/total:.1%} {private/total:.1%} {ideal/total:.1%}')
 hops=re.findall(r'\[ACTOR_JOIN\] (\d+) '+str(k)+r' (\w+) (\w+) (\w+) (\d+) (\d+) (\d+)',s)
 blocks=Counter();sites=Counter()
 for _,address,writer,reader,_,_,_ in hops:
  blocks[int(address,16)&~15]+=1;sites[(symbol(writer),symbol(reader))]+=1
 print('16-byte operands',[(hex(x),v) for x,v in blocks.most_common(10)]);print('writer -> reader',sites.most_common(8))
