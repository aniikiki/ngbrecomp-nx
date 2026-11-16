"""Attribute producer CPU samples by the consumer's actual decision on that emitted command."""
from pathlib import Path
import re
log=Path('build/switch-runtime/core-perf/opening-present-combined/cliprecord-base-1.log').read_text()
assert 'reason=verified 120 original demo frames' in log
rows=[tuple(map(int,m)) for m in re.findall(r'^\[CLIP_RECORD\] f=(\d+) cut=(\d+) cmds=(\d+) n=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+)$',log,re.M)]
assert [(f,c) for f,c,*_ in rows]==[(30,0),(30,1),(120,0),(120,1)]
for f,c,k,n,t,b,z in rows:
 assert 0<n and 0<b and n+b<=k
 print(f,'culled' if c else 'other',k,'real/empty',n,b,'corrected recorder ms per host frame',round(k*(t/n-z/b)/(30 if f==30 else 90)/1e6,4))
