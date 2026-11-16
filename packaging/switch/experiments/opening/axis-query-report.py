"""Estimate host cost; coverage of early gates is not an estimate of device savings."""
import re,sys
from pathlib import Path
s=Path(sys.argv[1]).read_text()
assert 'verified 120 original demo frames' in s
rows=[tuple(map(int,r)) for r in re.findall(r'^\[AXIS_QUERY\] (\d+) calls=(\d+) y=(\d+) z=(\d+) next=(\d+) reject_exit=(\d+) ns=(\d+) n=(\d+) blank=(\d+) b=(\d+) cross=(\d+)$',s,re.M)]
assert [r[0] for r in rows]==[30,120]
for f,c,y,z,n,rej,t,k,e,b,cross in rows:
 assert c>=y>=z>=n and k and b and not cross
 print(f'{f}: calls {c}, rejected at first three stages {c-y}/{y-z}/{z-n}, reached remainder {n}, sampled body {(t/k-e/b)*c/(30 if f==30 else 90)/1e6:.4f} ms/host frame')
