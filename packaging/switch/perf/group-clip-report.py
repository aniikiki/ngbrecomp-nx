"""Only count complete outermost callbacks whose every renderer command was excluded."""
from pathlib import Path
from collections import Counter,defaultdict
from struct import iter_unpack
import sys
base=Path(sys.argv[1])
rows=list(iter_unpack('<5I',(base/'mesh-cost.bin').read_bytes()))
cmd=Counter(iter_unpack('<2I',(base/'mesh-draw.bin').read_bytes()))
assert {f for _,f,*_ in rows}==set(range(1801,1921))
assert {s for s,_ in cmd}<=set(row[0] for row in rows)
assert len(rows)==len({row[0] for row in rows})
table=defaultdict(Counter)
for seq,f,cb,n,ns in rows:
    assert cmd[seq,0]+cmd[seq,1]==n,(seq,n,cmd[seq,0],cmd[seq,1])
    k='empty' if not n else 'all_out' if cmd[seq,1]==n else 'mixed' if cmd[seq,1] else 'none_out'
    g=table[cb];g[k]+=1;g[k+'_ns']+=ns;g['ns']+=ns;g['cmd']+=n;g['out']+=cmd[seq,1];g['all_out_cmd']+=n if k=='all_out' else 0
print('outer callbacks, tags and all draw counts reconciled:',len(rows),sum(cmd.values()))
for cb,g in sorted(table.items(),key=lambda x:-x[1]['ns']):
    print(f"{cb:08x} groups no/mixed/all outside/empty={g['none_out']}/{g['mixed']}/{g['all_out']}/{g['empty']}; draws outside in all-out groups / outside / all={g['all_out_cmd']}/{g['out']}/{g['cmd']}; CPU all-out/all {g['all_out_ns']/120e6:.4f}/{g['ns']/120e6:.4f} ms/frame")
