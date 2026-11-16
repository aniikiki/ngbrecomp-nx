"""Qualify sampled material elapsed time with thread CPU on the same hardware frames."""
import re, sys
from pathlib import Path
s = Path(sys.argv[1]).read_text()
# Verify the first two snapshots belong to the continuous first opening.
blocks = re.split(r'^\[SERVICE\] 3D scene window frames=', s, flags=re.M)[1:3]
last = (0, 0, 0)
cpu = {int(f): int(t) for f,t in re.findall(r'\[DRAW_BOUND\] frame=(\d+) draws=\d+ ticks=\d+ cpu=(\d+) rc=0',s)}
assert sorted(cpu)==list(range(31,121))
for b,lo,hi in zip(blocks,(1,31),(30,120)):
    assert int(b.split()[0])==hi-lo+1 and int(re.search(r'3D scene flips=(\d+)',b)[1])==hi
    mesh,other = map(int,re.search(r'sampled material setters in_mesh_us=(\d+) outside_mesh_us=(\d+)',b).groups())
    curr = int(re.search(r'sampled_frames=(\d+)',b)[1]),mesh,other
    n,m,o = (v-w for v,w in zip(curr,last));last=curr
    frames=[f for f in range(lo,hi+1) if (f-1)%16 == (9*((f-1)//16))%16]
    assert n==len(frames)
    print(frames,'material ms per sampled frame (mesh, other):',m/n/1000,o/n/1000)
    if lo==31:
        hz=19200000 # Tegra system counter used for DRAW_BOUND
        avg=sum(cpu[f] for f in frames)*1000/hz/n
        print('sampled CPU',avg,'CPU minus measured material elapsed',avg-(m+o)/1000/n,
              'all 90 CPU',sum(cpu.values())*1000/hz/90)
