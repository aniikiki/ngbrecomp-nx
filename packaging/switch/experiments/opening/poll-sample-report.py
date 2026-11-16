"""CPU samples on the emulated CPU only. Never turn sample shares into Switch milliseconds."""
import re
from pathlib import Path
s=Path('build/switch-runtime/core-perf/opening-poll-sample/distribution.log').read_text()
assert 'verified 120 original demo frames' in s
windows=re.findall(r'^\[POLL_SAMPLE\] (.*)$',s,re.M)
assert len(windows)==2
for end,line in zip((30,120),windows):
 f,lost,*v=map(int,line.split());n=sum(v)
 assert f==end and len(v)==6 and n>0
 print(f'f{f}, {n} delivered / {lost} overruns, non-callback housekeeping {sum(v[1:5])}/{n} ({sum(v[1:5])/n:.1%}); guest callback {v[5]}/{n}; device/voice/scheduler/timer: {v[1:5]}')
