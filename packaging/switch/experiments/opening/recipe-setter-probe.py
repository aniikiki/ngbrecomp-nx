"""Increment counts at actual A64 calls, preserving flags and scratch registers."""
from pathlib import Path
import re,subprocess
def install(p,regs):
 s=(regs/'recomp_0028.c.gated.s').read_text()
 def patch(s,fn,callee,idx,expected):
    title='\nngb_reg_sub_'+fn+':\n';start=s.index(title)+len(title);end=s.index('\n\t.size\tngb_reg_sub_'+fn+',',start)
    needle=r'(?m)^(\s*bl[ \t]+'+callee+r'[ \t]*)$'
    code=f'\tstp x16,x17,[sp,#-16]!\n\tadrp x16,recipe_calls\n\tadd x16,x16,:lo12:recipe_calls\n\tldr w17,[x16,#{idx*4}]\n\tadd w17,w17,#1\n\tstr w17,[x16,#{idx*4}]\n\tldp x16,x17,[sp],#16\n'
    b,n=re.subn(needle,lambda m:code+m[0],s[start:end]);assert n==expected,(callee,n)
    return s[:start]+b+s[end:]
 for idx,(name,n) in enumerate((('003C9030',1),('003C8710',1),('003C5C60',6),('003C5340',1),('003C5BE0',1),('003C5500',1),('003C5460',1),('0030D630',1))):
    s=patch(s,'0030B7E0',('ngb_gate_sub_' if idx<7 else 'ngb_reg_sub_')+name,idx,n)
 s=patch(s,'0030D630','ngb_gate_ngb_guest_pointer',8,4)
 f=p.out/'setter-observe.s';o=f.with_suffix('.o')
 try:
    f.write_text(s);subprocess.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc','-c',str(f),'-o',str(o)],check=True)
 finally:f.unlink(missing_ok=True)
 p.link[p.link.index(str(regs/'recomp_0028.c.o'))]=str(o)
