"""Offline upper bounds on grouping consecutive hidden submissions; history is not a cull test."""
from collections import Counter, defaultdict
from itertools import groupby
from pathlib import Path
from statistics import mean
from struct import iter_unpack
import sys

def analyze(root):
    cmds=Counter(iter_unpack('<2I',(root/'mesh-draw.bin').read_bytes()))
    windows=defaultdict(list)
    seen=set()
    for seq,f,mesh,n,cpu in iter_unpack('<5I',(root/'mesh-cost.bin').read_bytes()):
        if seq in seen or n!=cmds[seq,0]+cmds[seq,1]:
            raise ValueError('duplicate producer or incomplete draw verdict')
        seen.add(seq)
        windows[f].append((mesh,n>0 and cmds[seq,1]==n,cpu))
    if set(windows)!=set(range(1801,1921)) or any(s not in seen for s,c in cmds):
        raise ValueError('incomplete frame or unmatched renderer verdict')
    runs=Counter();history={};pred=Counter();keys=defaultdict(set);all_ns=outside=0
    for f, rows in sorted(windows.items()):
        occurrence=Counter();current={}
        for mesh,hidden,cpu in rows:
            ref=mesh,occurrence[mesh];occurrence[mesh]+=1
            if ref in history:pred[history[ref],hidden]+=1
            current[ref]=hidden
            keys[mesh].add(hidden);all_ns+=cpu
        history=current
        for hidden,block in groupby(rows,key=lambda r:r[1]):
            block=list(block)
            if hidden:runs[len(block)]+=1;outside+=sum(r[2] for r in block)
    print('frames',len(windows),'unique mesh values',len(keys),'both outcomes',sum(len(v)>1 for v in keys.values()))
    print('hidden submissions',sum(k*v for k,v in runs.items()),'contiguous runs',sum(runs.values()),'max length',max(runs,default=0),'top lengths',runs.most_common(12))
    print('prior hidden same mesh+ordinal: hidden now',pred[True,True],'visible/unproven now',pred[True,False])
    print('enclosing mesh CPU ms/frame %.4f; entirely hidden subset %.4f (%.1f%%)'%(all_ns/120e6,outside/120e6,100*outside/all_ns))
if __name__=='__main__':analyze(Path(sys.argv[1]))
