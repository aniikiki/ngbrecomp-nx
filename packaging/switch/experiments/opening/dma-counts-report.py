"""Report observed calls and GCC source-line counts, not CPU time or exact bus traffic."""
from pathlib import Path
import json,gzip,re
d=Path('build/switch-runtime/core-perf/opening-rng-correspondence')
assert 'reason=verified 120 original demo frames' in (d/'dma-coverage.log').read_text()
files=json.loads(gzip.decompress((d/'host/nv2a_boot.c.gcov.json.gz').read_bytes()))['files']
src=next(f for f in files if f['file'].endswith('/nv2a_boot.c'))
lines=(d/'host/nv2a_boot.c').read_text().splitlines()
print('late 90 flips: function entry counts (includes compiler inlining attribution)')
for f in src['functions']:
 if f['name'] in ('execute_dma','dma_word','dispatch_method','retire_state_packets','state_packet_size','direct_state_words','ngb_mmio_write'):
  print(f['name'],f['execution_count'])
for needle in ('uint32_t word = dma_word(base,','unsigned retired = retire_state_packets','*get += retired;','param_count += consumed;','else dispatch_method(sub, method, word);','memcpy(&header, mapped +','trace("DMA jump",'):
 ids=[i for i,s in enumerate(lines,1) if needle in s];assert len(ids)==1
 counts=[int(l['count']) for l in src['lines'] if l['line_number']==ids[0]]
 print('line',ids[0],needle,counts or 'not mapped')
