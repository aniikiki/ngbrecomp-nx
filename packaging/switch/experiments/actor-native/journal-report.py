"""Refuse incomplete captures, mismatches, and empty IRQ windows."""
import sys,re
from pathlib import Path
s=Path(sys.argv[1]).read_text()
if 'reason=verified original combat window' not in s:sys.exit('incomplete reference replay')
def rows(tag):
 return [{k:int(v,16 if k=='error' else 10) for k,v in re.findall(r'(\w+)=([0-9a-f]+)(?:\s|$)',l)} for l in s.splitlines() if l.startswith('['+tag+']')]
r=rows('IRQ_COMPARE');m=rows('IRQ_MEMORY');j=rows('WORKER_NATIVE')
if not r or len(r)!=len(j) or not sum(v['boundaries'] for v in r):sys.exit('empty or unpaired checkpoint capture')
print(f"{len(r)} jobs, {sum(v['boundaries'] for v in r)} real poll service boundaries, {sum(v['bad'] for v in r)} register mismatches")
if m:print(f"{sum(v['bytes'] for v in m):,} bytes sampled at IRQ boundaries, {sum(v['diff'] for v in m):,} differing, {sum(v['journal'] for v in m):,} private byte-store events")
if (m and len(m)!=len(j)) or any(v['bad'] for v in r+m) or any(any(v[k] for k in ('error','byte_diff','nonstack','unseen_writes','regs')) for v in j):sys.exit(1)
