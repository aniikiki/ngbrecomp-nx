"""Check actual Switch compiler settings and resulting code. Do not touch built objects."""
import shlex,subprocess as sp,tempfile
from pathlib import Path
b=Path('/work/build/switch-runtime/switch')
rows=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=b,text=True).splitlines()
c,=[shlex.split(x) for x in rows if x.endswith('/packaging/switch/runtime/runtime.c')]
assert c.count('-O1')==1 and '-mtune=cortex-a57' in c
with tempfile.TemporaryDirectory() as tmp:
 for level in (1,2):
  f=Path(tmp)/f'rt{level}.o';cmd=c.copy()
  if level==2:cmd[cmd.index('-O1'):cmd.index('-O1')+1]=['-O2','-fno-strict-aliasing']
  cmd[cmd.index('-o')+1]=str(f);cmd[cmd.index('-MF')+1]=str(f)+'.d'
  sp.run(cmd,cwd=b,check=True)
  out=sp.check_output([c[0].removesuffix('gcc')+'nm','-S','--defined-only',f],text=True)
  symbols={v[3]:int(v[1],16) for l in out.splitlines() if len(v:=l.split())==4 and v[2] in ('T','t')}
  pick=['ngb_checkpoint','ngb_poll_due','ngb_guest_pointer','yield_worker','poll_callbacks']
  assert all(v in symbols for v in pick[:3])
  print(level,{k:symbols.get(k) for k in pick},'text symbol bytes',sum(symbols.values()),flush=True)
