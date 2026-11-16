"""Low-overhead probe: only snapshot guest regs at service points inside a
short span with no context switch. Compare to exact trace. Capture *all*
polls by setting stride 1. Abort rather than publishing an unknown phase."""
from pathlib import Path
h=Path(__file__).resolve().parent;s=(h/'checkpoint-build.py').read_text();a=s.index("exec(compile(s,'checkpoint-worker'")
s=s[:a]+'''s=s.replace("d=p/'opt050/actor-checkpoints'","d=p/'opt050/actor-window'")
s=s.replace('unsigned stride,events;', 'unsigned stride,events,mask,base,stats;')
s=s.replace('unsigned *events){','unsigned *events,unsigned mask){ac.mask=mask;ac.base=(unsigned)*polls;ac.stats=0;')
s=s.replace(' unsigned char *dst=ac.trace+', ' if(((ac.base+ac.events)&ac.mask)!=0)return;ac.stats++; unsigned char *dst=ac.trace+')
'''+s[a:];exec(compile(s,'window-generator','exec'))
