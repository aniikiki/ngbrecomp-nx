"""Summarize real speculative completions. Fail closed on partial replays."""
import re,sys,statistics
from pathlib import Path
s=Path(sys.argv[1]).read_text()
rows=[{k:int(v,16 if k=='error' else 10) for k,v in re.findall(r'(\w+)=([0-9a-f]+)',l)} for l in s.splitlines() if l.startswith('[WAVE]')]
if 'reason=verified original combat window' not in s or len(rows)!=60 or {(r['wave'],r['pos']) for r in rows}!={(w,p) for w in range(1,7) for p in range(1,11)}:sys.exit('incomplete six-wave reference')
bad=[r for r in rows if any(r[k] for k in ('error','diff','extra','regs'))]
print(f"{len(rows)-len(bad)}/{len(rows)} exact jobs, {sum(r['writes'] for r in rows):,} original written bytes, mismatching positions {sorted({r['pos'] for r in bad})}")
for l in s.splitlines():
 if l.startswith('[WORLD_SNAPSHOT]'):print(l)
times=[(int(a)/8000,int(b)/8000) for a,b in re.findall(r'\[WAVE_BENCH\] wave=\d+ serial8=(\d+) parallel8=(\d+)',s)]
if times:print(f"ten-job p50: serial {statistics.median(a for a,b in times):.2f} us parallel {statistics.median(b for a,b in times):.2f} us ({len(times)} paired blocks); excludes snapshot, publication and game callbacks")
sys.exit(bool(bad))
