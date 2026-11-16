"""Report cross-task changed-byte reads from an offline ARM combat replay."""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('log', type=Path)
ap.add_argument('symbols', type=Path, help='nm -n -S --defined-only replay')
args = ap.parse_args()
symbols = []
for line in args.symbols.read_text().splitlines():
    cols = line.split()
    if len(cols) == 4 and cols[2] in ('t','T'):
        symbols.append((int(cols[0],16), int(cols[1],16), cols[3]))
symbols.sort()
starts = [s[0] for s in symbols]

def name(ret):
    pc = int(ret,16) - 4
    i = bisect_right(starts,pc) - 1
    if i >= 0:
        start,size,sym = symbols[i]
        if pc < start + size:
            return sym.removeprefix('alt_')
    return '?'+ret

frames, edges, sites = [], Counter(), defaultdict(Counter)
totals = Counter()
dropped = None
completed = False
for line in args.log.open():
    cols = line.split()
    if not cols: continue
    if cols[0]=='[RESULT]':
        completed |= 'verified original combat window' in line
    elif cols[0]=='[FLOW_FRAME]':
        frames.append(int(cols[1]))
    elif cols[0]=='[FLOW]' and cols[2]=='0':
        edges[int(cols[3]),int(cols[4])] += int(cols[5])
    elif cols[0]=='[FLOW_SITE]':
        a,b,w,r,addr,n=cols[1:]
        edge=(int(a),int(b))
        sites[edge][name(w),name(r)] += int(n)
        totals[edge] += int(n)
    elif cols[0]=='[FLOW_LOST_SITES]':
        dropped=int(cols[1])
if not completed or frames!=list(range(1801,1806)) or dropped!=0 or totals!=edges:
    raise SystemExit('Incomplete frame window, replay, or site attribution')
roles=['?', 'render', 'update-A', 'update-B', 'update-C', 'other']
for (a,b),count in edges.most_common():
    top=sites[a,b].most_common(2)
    print(f'{roles[a]:8} -> {roles[b]:8} {count/len(frames):9.1f} byte reads/frame; '+
          '; '.join(f'{w} -> {r} ({n/count:.1%})' for (w,r),n in top))
