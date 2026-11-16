"""Compare executed node discriminators with independent direct root-edge counts."""
from pathlib import Path
import re
base=Path('build/switch-runtime/core-perf')
def verified(name):
 s=(base/f'opening-{name}'/'distribution.log').read_text()
 assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
 return s
s=verified('actor-kinds');e=verified('task-edges')
for f,n in [(30,30),(120,90)]:
 line,=re.findall(rf'^\[ACTOR_KINDS\] {f} (.+)$',s,re.M);v=list(map(int,line.split()));assert len(v)==17 and sum(v)
 roots=sum(map(int,re.findall(rf'^\[CB_COST\] {f} bd00002[cd] (\d+) \d+$',e,re.M)))
 print(f'{f-n+1}..{f}: {sum(v)/n:.1f} node visits/frame, {roots/n:.1f} direct CBD00 edges/frame in separate reference; early-return types 0+1: {sum(v[:2])}/{sum(v)} ({sum(v[:2])/sum(v):.1%}); all kinds:',{i:c for i,c in enumerate(v) if c})
