"""Rank the remaining units by observed transitions in and out of register
code. Exclude host work and same-function loops; counts are not CPU cycles."""
from pathlib import Path
import re,bisect,collections
p=Path('build/switch-runtime');d=p/'opt050';units={}
for f in (p/'gen').glob('recomp_[0-9]*.c'):
 for fn in re.findall(r'^void ((?:sub_|d3d_orig_)[A-F0-9]+)\(void\)',f.read_text(),re.M):units[fn]=int(f.stem[-4:])
a=[]
for l in (d/'codetrace/host-symbols.txt').open():
 v=l.split()
 if len(v)!=4 or v[2] not in 'tT':continue
 pc,n=int(v[0],16),int(v[1],16);fn=v[3].removeprefix('ngb_reg_').removeprefix('ngb_gate_').split('.')[0]
 if n and fn in units:a.append((pc,n,units[fn],fn))
a.sort();starts=[x[0] for x in a]
def lookup(pc):
 i=bisect.bisect_right(starts,pc)-1
 return a[i][2:] if i>=0 and pc<a[i][0]+a[i][1] else (-1,'')
edges=collections.Counter()
for l in (d/'bolt/edges').open():
 x,y,n=l.split();i,fn=lookup(int(x,16));j,gn=lookup(int(y,16))
 if min(i,j)>=0 and i!=j and fn!=gn:edges[i,j]+=int(n)
orig={0,1,2,3,9,10,11,14,16,27,28,29,37,44}
for k in sorted(set(units.values())-orig,key=lambda k:-sum(edges[k,i]+edges[i,k] for i in orig))[:12]:
 print(k,sum(edges[k,i]+edges[i,k] for i in orig))
