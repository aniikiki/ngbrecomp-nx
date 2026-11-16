"""Change only the position of the whole register file inside one constant-sized BSS block."""
def install(p,src,offset):
 from pathlib import Path
 assert offset in (0,8)
 s=(p.out/'host-runtime.inc').read_text()
 decl='RecompRegs g_regs;'
 assert s.count(decl)==2
 v=r'''_Static_assert(sizeof(RecompRegs)==312 && _Alignof(RecompRegs)<=8,"register layout");
_Static_assert(__builtin_offsetof(RecompRegs,r_xmm0)==120,"vector bank offset");
__asm__(".pushsection .bss.opening_reg_storage,\u005c"aw\u005c",%nobits\u005cn"
        ".balign 64\u005cn.global opening_reg_storage\u005cnopening_reg_storage:\u005cn"
        ".space OFFSET\u005cn.global g_regs\u005cn.type g_regs,%object\u005cng_regs:\u005cn"
        ".space 312\u005cn.size g_regs,312\u005cn.space TAIL\u005cn.popsection");'''.replace(r'\u005c',chr(92)).replace('OFFSET',str(offset)).replace('TAIL',str(72-offset))
 (p.out/'align-runtime.inc').write_text(s.replace(decl,v))
 assert src.count('"host-runtime.inc"')==1
 return src.replace('"host-runtime.inc"','"align-runtime.inc"')
