"""Resolve menu-pc.csv or a historical mission-pc.csv using symbols.gz from the matching NRO."""
from argparse import ArgumentParser
from bisect import bisect_right
from collections import Counter
import csv
import gzip

def read_symbols(path):
    names = {}
    with gzip.open(path, "rt") as source:
        for line in source:
            cols = line.split()
            if len(cols) in (3, 4) and cols[-2] in ("T", "t", "W", "w"):
                addr = int(cols[0], 16)
                size = int(cols[1], 16) if len(cols) == 4 else 0
                if addr not in names or size > names[addr][1]:
                    names[addr] = cols[-1], size
    return sorted(names), names

def report(trace, symbols):
    starts,names = read_symbols(symbols)
    def label(addr):
        i = bisect_right(starts,addr)-1
        if i < 0 or addr == 0xffffffff: return "(outside NRO)"
        base = starts[i]
        name,size = names[base]
        if size and addr>=base+size or not size and i==len(starts)-1 and addr!=base:
            return "(no symbol)"
        return name
    pcs,lrs,errors=Counter(),Counter(),Counter()
    cost=0
    with open(trace) as f:
        for row in csv.DictReader(f):
            rc=int(row["rc"],16)
            if rc:
                errors[hex(rc)]+=1
                continue
            pcs[label(int(row["pc_offset"],16))]+=1
            lr=int(row["lr_offset"],16)
            lrs[label(lr-4 if 4<=lr<0xffffffff else lr)]+=1
            cost+=int(row["sample_us"])
    print(f"Valid snapshots: {sum(pcs.values())}; sampling cost: {cost/1000:.2f} ms; errors: {dict(errors)}")
    for kind,counts in (("PC",pcs),("LR",lrs)):
        for name,n in counts.most_common(15):print(f"{kind} {n:5d} {name}")
    print("Snapshots may include blocked time. LR is a return address, not an independent sample.")

if __name__=="__main__":
    p=ArgumentParser(description=__doc__);p.add_argument("trace");p.add_argument("symbols")
    a=p.parse_args();report(a.trace,a.symbols)
