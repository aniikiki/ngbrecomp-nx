"""Align the measured high-entry primary sections only, without recompiling game code."""
from pathlib import Path
import subprocess as sp,re
p=Path('build/switch-runtime/core-perf')
base=p/'opening-partition-pgo';out=p/'opening-align-hot-entry';out.mkdir(exist_ok=True)
work=[r.split() for r in (p/'opening-retained-pgo/call-work.txt').read_text().splitlines()[1:]]
top=sorted(((int(n),int(u),fn) for u,fn,callee,n,_ in work if callee=='ngb_checkpoint'),reverse=True)[:32]
for u in (2,10,16,28,29):
 f=f'recomp_{u:04}.c.o';sections={}
 prefix='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-'
 def layout(o):
  return {m[1]:int(m[2]) for m in re.finditer(r'^\s*\[\s*\d+\]\s+(\S+)\s+PROGBITS\s+.*?\s+AX\s+\d+\s+\d+\s+(\d+)\s*$',sp.check_output([prefix+'readelf','-SW',o],text=True),re.M)}
 old=layout(base/f);cmd=[]
 for _,unit,fn in top:
  if unit!=u:continue
  matches=[s for s in old if s in ('.text.'+fn,'.text.hot.'+fn)]
  assert len(matches)==1,(fn,matches)
  sec=matches[0];sections[sec]=max(old[sec],64)
  cmd+=['--set-section-alignment',sec+'='+str(sections[sec])]
 sp.run([prefix+'objcopy',*cmd,base/f,out/f],check=True)
 assert layout(out/f)==dict(old,**sections)
 print(u,len(sections),flush=True)
print('training checkpoint weight selected / all',sum(x[0] for x in top),sum(int(n) for u,fn,c,n,_ in work if c=='ngb_checkpoint'))
(out/'entries.txt').write_text('\n'.join(fn for _,_,fn in top)+'\n')
