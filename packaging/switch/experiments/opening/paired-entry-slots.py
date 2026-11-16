"""Leave public ABI bodies intact; use alignment padding for their private branch."""
from pathlib import Path
import re,subprocess as sp
def generate(src,gates):
 parts=re.findall(r'^\.global (\w+)\n\.type \1,%function\n\1:\n(.*?)^\.size \1,\.-\1$',src,re.M|re.S)
 assert len(parts)==src.count('\n.global ') and len(set(n for n,b in parts))==len(parts)
 entry='.text\n.p2align 7\n.global ngb_slot_start\n.hidden ngb_slot_start\nngb_slot_start:\n'
 for n,body in parts:
  assert body.count(f' bl ngb_reg_{n}\n')==1 and body.endswith(' ret\n') and len(body.splitlines())<=31
  entry+=f'.global {n}\n.type {n},%function\n{n}:\n{body}.size {n},.-{n}\n.space {124-4*len(body.splitlines())}\nb ngb_reg_{n}\n'
 entry+='.section .note.GNU-stack,"",%progbits\n'
 k='ngb_gate_indirect:\n';assert gates.count(k)==1
 gates=gates.replace(k,k+f''' adrp x17,ngb_slot_start
 add x17,x17,:lo12:ngb_slot_start
 sub x17,x16,x17
 tst x17,#127
 b.ne 1f
 lsr x17,x17,#7
 mov w15,#{len(parts)}
 cmp x17,x15
 b.hs 1f
 add x16,x16,#124
 br x16
1:
''')
 return entry,gates
def install(p,d):
 entry,gates=generate((d/'entry.S').read_text(),(d/'gates.s').read_text())
 for n,s in [('entry',entry),('gates',gates)]:
  f=p.out/('paired-slot-'+n+'.S');obj=f.with_suffix('.o')
  try:
   f.write_text(s);sp.run(['cc','-c',f,'-o',obj],check=True)
   if n=='entry':
    names=re.findall(r'^\.global (\w+)$',(d/'entry.S').read_text(),re.M)
    sy={n:int(a,16) for a,n in re.findall(r'^([a-f0-9]+) [Tt] (\w+)$',sp.check_output(['nm',obj],text=True),re.M)}
    r={int(a,16):n for a,n in re.findall(r'^([0-9a-f]+)\s+\S+\s+R_AARCH64_JUMP26\s+\S+\s+(\w+) \+ 0$',sp.check_output(['readelf','-rW',obj],text=True),re.M)}
    assert len(r)==len(names) and all(sy[name]==128*i and r[128*i+124]=='ngb_reg_'+name for i,name in enumerate(names))
    print('verified public offsets and private branch relocations',len(names),flush=True)
  finally:f.unlink(missing_ok=True)
  p.link[p.link.index(str(d/(n+'.o')))]=str(obj)
