"""Inclusive budget of two top-level child traversals, averaged over the opening windows."""
import re,sys
from pathlib import Path
s=Path(sys.argv[1]).read_text()
assert 'verified 120 original demo frames' in s
rows=[tuple(map(int,r)) for r in re.findall(r'^\[TREE_COST\] (\d+) (\d+) calls=(\d+) samples=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+) cross=(\d+)$',s,re.M)]
assert [(r[0],r[1]) for r in rows]==[(30,0),(30,1),(120,0),(120,1)]
for f,i,n,k,t,b,e,c in rows:
 assert k and b and not c
 print(f'{f=} pass={i} top calls={n} timed={k} mean inclusive CPU {(t/k-e/b)*n/(30 if f==30 else 90)/1e6:.4f} ms/host frame')
