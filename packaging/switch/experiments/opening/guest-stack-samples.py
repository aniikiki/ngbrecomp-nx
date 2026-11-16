"""Recheck only interrupted PCs; distinguish actual SP operands from x29,
which a compiler can use as a general register in frameless functions."""
from pathlib import Path
import re,collections
base=Path('build/switch-runtime')
c=collections.Counter();leaves=[]
with (base/'history/0.51.0-rc1/ngb-startup.nro').open('rb') as n:
 for l in (base/'core-perf/opening-setup/leaf-budget.tsv').read_text().splitlines():
    row=l.split('\t')
    if len(row)<7 or not 31<=int(row[0])<=120:continue
    c['all']+=1
    if not re.match(r'(ngb_reg_)?(sub_|d3d_orig_)',row[3]):continue
    c['guest']+=1
    op,arg=row[5:7]
    if not re.search(r'\[sp(?:,|\])',arg):continue
    c['sp operand']+=1
    if op=='stp' and re.fullmatch(r'x29, x30, \[sp, #-(\d+)\]!',arg):
        n.seek(int(row[2],16));word=int.from_bytes(n.read(4),'little')
        assert word & 0xffc07fff == 0xa9807bfd
        c['save fp/lr']+=1;leaves.append(row[3])
print(dict(c),leaves)
