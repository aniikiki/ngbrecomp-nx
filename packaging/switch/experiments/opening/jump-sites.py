"""Rank local indirect-branch sites for probing, not a branch execution count."""
from pathlib import Path
import collections,re
base=Path('build/switch-runtime')
log=(base/'core-perf/opening-setup/entry-mix.log').read_text()
assert 'verified 120 original demo frames' in log
entries=collections.Counter()
rows=re.findall(r'^\[ENTRY_MIX\] (\d+) ([^\n]*)',log,re.M)
assert [int(f) for f,_ in rows]==list(range(1,121))
for f,line in rows[30:]:
    entries.update({int(k,16):int(v) for k,v in re.findall(r'(\w+):(\d+)',line)})
candidates=[]
for c in (base/'gen').glob('recomp_*.c'):
    chunks=re.split(r'\bRECOMP_ENTRY\(0x([0-9A-Fa-f]+)u\);',c.read_text())
    for addr,body in zip(chunks[1::2],chunks[2::2]):
        sites=list(map(int,re.findall(r'/\* switch: \d+ entries, (\d+) targets \*/',body)))
        if sites and entries[int(addr,16)]:
            candidates.append((entries[int(addr,16)]/90,addr,sites,c.name))
print("Top functions containing jump tables: entries per frame, address, distinct targets per site, unit")
for row in sorted(candidates,reverse=True)[:10]:print(round(row[0],1),*row[1:])
