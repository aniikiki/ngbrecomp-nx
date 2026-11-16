"""Report original XDK interception sites inside the outermost mesh call."""
from collections import Counter, defaultdict
from pathlib import Path
import re
from struct import Struct
import sys

names = {int(v): k for k,v in re.findall(r'D3DF_(\w+) = (\d+)', Path('src/d3d/d3d_funcs.h').read_text())}
sites, chains, totals = Counter(), Counter(), Counter()
sequence = None
prior, current = defaultdict(list), defaultdict(list)
same = compared = submissions = 0
frame = 1800
for kind, a, b in Struct('<III').iter_unpack(Path(sys.argv[1]).read_bytes()):
    if kind == 1:
        assert sequence is None
        if a != frame:
            assert a == frame + 1
            frame, prior, current = a, current, defaultdict(list)
        mesh, sequence = b, []
    elif kind == 2:
        assert sequence is not None
        sequence.append((a,b))
        sites[a,b] += 1
        totals[a] += 1
    else:
        assert kind == 3 and sequence is not None
        seq = tuple(sequence)
        n = len(current[mesh])
        if frame > 1801 and n < len(prior.get(mesh, ())):
            compared += 1
            same += seq == prior[mesh][n]
        current[mesh].append(seq)
        chains[seq] += 1
        sequence = None
        submissions += 1
assert frame == 1920 and sequence is None and compared
print(f'{submissions} submissions; {sum(totals.values())} intercepted calls; {len(chains)} different chains')
print(f'{same}/{compared} matched mesh occurrences had the same ordered sites')
for (fn, pc), n in sites.most_common(20):
    print(f'{n/120:7.1f}/frame {pc:08x} {names[fn]}')
for seq, n in chains.most_common(8):
    print(f'{n:6} submissions:', ' '.join(names[fn] for fn, _ in seq) or '(no interception)')
