"""Train section order on 1800–1801; estimate its effect on separate 1802–1803.

Only original guest/ABI functions with matching host and NRO symbol sizes
participate. This is an instruction *fetch locality* experiment, not a
processor simulator, time measurement, or hardware performance prediction.
"""
import argparse,bisect,collections,functools,gzip,mmap,re,struct
from pathlib import Path

ap=argparse.ArgumentParser(description=__doc__)
for arg in ('trace','host_nm','nro_nm','order'):ap.add_argument(arg,type=Path)
ap.add_argument('--actual',type=Path,help='nm after relinking the real Switch ELF')
args=ap.parse_args()
def symbols(path):
    names={}
    with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as f:
        for line in f:
            a=line.split()
            if len(a)!=4 or a[2] not in ('t','T'):continue
            addr,n,s=int(a[0],16),int(a[1],16),a[3]
            if n and re.fullmatch(r'(?:(?:ngb_reg_|ngb_gate_)?(?:sub_|d3d_orig_)[0-9A-F]+|ngb_gate_\w+|ngb_reg_checkpoint|xbe_entry_point)',s):
                names[s]=(addr,n)
    return names
host,nro=symbols(args.host_nm),symbols(args.nro_nm)
funcs=sorted((addr,n,name,nro[name][0]) for name,(addr,n) in host.items() if name in nro and n==nro[name][1])
starts=[f[0] for f in funcs]
@functools.lru_cache(None)
def resolve(pc,size):
    i=bisect.bisect_right(starts,pc)-1
    if i>=0 and pc+size<=starts[i]+funcs[i][1]:return i,pc-starts[i]
    return -1,0
f=args.trace.open('rb')
mm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
sig,base,end,n=struct.unpack_from('<4Q',mm)
assert sig==0x4e4742434f444531 and len(mm)==32+n*16
def events():return struct.iter_unpack('<QII',memoryview(mm)[32:])
holdout=collections.Counter();hot=collections.Counter();adj=collections.Counter();cover=collections.Counter()
prev=-1
for pc,size,frame in events():
    cover[frame,0]+=size//4
    i,off=resolve(pc-base,size) if base<=pc<end else (-1,0)
    if i<0:
        prev=-1
        continue
    cover[frame,1]+=size//4
    if frame>=1802:holdout[i]+=size//4
    if frame<=1801:
        hot[i]+=size//4
        if prev>=0 and prev!=i:adj[prev,i]+=1
        prev=i
if {k[0] for k in cover}!=set(range(1800,1804)):raise ValueError('Incomplete trace window')
# Merge chains along frequently traversed boundaries. Preserve each function as
# an indivisible unit: every internal label, jump table and unwind range stays put.
chains={i:[i] for i in hot};owner={i:i for i in hot}
for (a,b),w in adj.most_common():
    x,y=owner[a],owner[b]
    if x==y or chains[x][-1]!=a or chains[y][0]!=b:continue
    if sum(funcs[i][1] for i in chains[x]+chains[y])>65536:continue
    for i in chains[y]:owner[i]=x
    chains[x]+=chains.pop(y)
order=[i for chain in sorted(chains.values(),key=lambda c:-sum(hot[i] for i in c)/sum(funcs[i][1] for i in c)) for i in chain]
order.extend(i for i in sorted(range(len(funcs)),key=lambda i:funcs[i][3]) if i not in hot)
args.order.write_text(''.join(funcs[i][2]+'\n' for i in order if i in hot))
def placed(items):
    pos=0;loc={}
    for i in items:
        pos=(pos+31)&~31
        loc[i]=pos
        pos+=funcs[i][1]
    return loc
# Three controls: existing NRO, existing function order repacked with identical
# alignment, trained order repacked. TLB is a sensitivity model only.
layouts=[{i:f[3] for i,f in enumerate(funcs)},placed(sorted(range(len(funcs)),key=lambda i:funcs[i][3])),placed(order)]
if args.actual:
    target=symbols(args.actual)
    if any(f[2] not in target or target[f[2]][1]!=f[1] for f in funcs):
        raise ValueError('Relinked symbol disappeared or changed size')
    layouts.append({i:target[f[2]][0] for i,f in enumerate(funcs)})

print('blocks',n,'matched functions',len(funcs),'trained functions',len(hot),flush=True)
for frame in range(1800,1804):print('frame',frame,'mapped/total instructions',cover[frame,1],cover[frame,0],flush=True)
for i,count in holdout.most_common(20):print('hot function',funcs[i][2],count,round(100*count/sum(holdout.values()),2),'% of mapped instructions',flush=True)
import subprocess
table=args.order.with_suffix('.ranges')
table.write_text(str(len(layouts))+'\n'+''.join(' '.join(map(str,[f[0],f[1],*(loc[i] for loc in layouts)]))+'\n' for i,f in enumerate(funcs)))
sim=args.order.parent/'layout-sim'
subprocess.run(['c++','-O2','-std=c++17',Path(__file__).with_name('sim.cpp'),'-o',sim],check=True)
subprocess.run([sim,table,args.trace],check=True)
