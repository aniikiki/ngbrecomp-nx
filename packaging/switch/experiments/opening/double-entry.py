"""Fuse immediately consecutive entry and label polls. Do not remove a ticket:
either may deliver work. A jump back to the first label uses the original
single label poll, unless the function has no jumps to that label."""
import re,os
from pathlib import Path
base=Path('/work/build/switch-runtime');abi=Path('/work/packaging/switch/arm-registers')
d=base/'core-perf/opening-double-entry';d.mkdir(exist_ok=True);os.environ['NGB_REG_OUT']=str(d)
hits=0
for i in (0,1,2,3,9,10,11,14,16,27,28,29,37,44):
 name=f'recomp_{i:04}.c';s=(base/'gen'/name).read_text()
 def fold(m):
  global hits
  body=m[0]
  pat=r'RECOMP_ENTRY\((0x([A-F0-9]+)u)\);\n\n(loc_\2): ; ngb_guest_block_poll\(\);'
  p=re.search(pat,body)
  if not p or body.count(p[3])!=1:return body
  hits+=1
  return body[:p.start()]+f'ngb_double_entry({p[1]});\n\n{p[3]}: ;'+body[p.end():]
 s=re.sub(r'^void (?:d3d_orig_|sub_)[0-9A-F]+\(void\)\n\{.*?^\}',fold,s,flags=re.S|re.M)
 (d/name).write_text('extern void ngb_double_entry(unsigned);\n'+s)
assert hits
print('fused pairs',hits,flush=True)
s=(abi/'compile.py').read_text()
k=' sp.run(c,cwd=w,check=True)';s=s.replace(k,' c[-1]=str(o/n)\n'+k)
exec(compile(s,'double-abi','exec'),{})
s=(abi/'gates.py').read_text()
k="  if t=='ngb_checkpoint':";s=s.replace(k,"  if t=='ngb_double_entry':return '\\tbl ngb_double_entry\\n'\n"+k)
exec(compile(s,'double-gates','exec'),{})
# Fast path is identical up to the poll predicate; use the original checkpoint
# for special startup entries. If either ticket can fire, start the unchanged
# first checkpoint before touching counters and re-evaluate the second ticket.
s=(abi/'checkpoint.S').read_text()
a=s.index('ngb_reg_checkpoint:\n');b=s.index('\tadrp\tx3, ngb_reg_current_va',a)
z=s.index('\tadrp\tx1, ngb_guest_polls',b)
entry=s[a:b].replace('ngb_reg_checkpoint:', 'ngb_double_entry:').replace('.LFB0:','').replace('bls\t.L2','bls\t9f').replace('beq\t.L2','beq\t9f')
entry+= '''    adrp x4,ngb_guest_polls
    ldr x5,[x4,:lo12:ngb_guest_polls]
    add x5,x5,#1
    adrp x6,ngb_poll_mask
    ldr w6,[x6,:lo12:ngb_poll_mask]
    tst x5,x6
    b.eq 9f
    add x5,x5,#1
    tst x5,x6
    b.eq 9f
    adrp x6,ngb_pending_dpcs
    ldr w6,[x6,:lo12:ngb_pending_dpcs]
    cbnz w6,9f
'''+s[b:z]+'''    str x5,[x4,:lo12:ngb_guest_polls]
    ldp x29,x30,[sp],16
    ret
9:  bl ngb_reg_checkpoint
    adrp x1,ngb_guest_polls
    ldr x0,[x1,:lo12:ngb_guest_polls]
    add x0,x0,1
    str x0,[x1,:lo12:ngb_guest_polls]
    adrp x1,ngb_poll_mask
    ldr w1,[x1,:lo12:ngb_poll_mask]
    tst x0,x1
    b.eq 8f
    adrp x1,ngb_pending_dpcs
    ldr w1,[x1,:lo12:ngb_pending_dpcs]
    cbz w1,7f
8:  bl ngb_gate_ngb_poll_due
7:  ldp x29,x30,[sp],16
    ret
    .cfi_endproc
'''
asm=d/'double.S'
asm.write_text(s[:s.index('.section .note')]+'.text\n.global ngb_double_entry\n.type ngb_double_entry,%function\n'+entry+'.size ngb_double_entry,.-ngb_double_entry\n.section .note.GNU-stack,"",%progbits\n')
import subprocess as sp
sp.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc','-c',asm,'-o',d/'checkpoint.o'],check=True)
for pat in ('recomp_*.s','recomp_*.c'):
 for f in d.glob(pat):f.unlink()
