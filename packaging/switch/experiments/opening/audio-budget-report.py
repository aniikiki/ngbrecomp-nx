from pathlib import Path
import re
s=Path('build/switch-runtime/core-perf/opening-audio-budget/budget.log').read_text()
assert 'reason=verified 120 original demo frames' in s
rows=[tuple(map(int,m.split())) for m in re.findall(r'^\[AUDIO_BUDGET\] ([0-9 ]+)$',s,re.M)]
assert [r[0] for r in rows]==[30,120]
for (end,c,idle,paused,n,t,b,e),frames in zip(rows,(30,90)):
 assert 0<n<c and 0<b<c and idle<=c and paused<=c
 print(end,'calls/frame',round(c/frames,2),'no active voices',round(idle/c,4),'paused',round(paused/c,4),'sample/control',n,b,'net host ms/frame',round((t/n-e/b)*c/frames/1e6,4))
