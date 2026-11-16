"""Resolve two ordinary input spans once and keep original SSE operations in locals."""
from pathlib import Path
import runpy,re
def transform(s,u):
 a=s.index('void sub_00011110(void)\n{');start=s.index('    xmm2 = XMM_SCALAR',a);end=s.index('    XMM_STORE(eax',start)
 old=s[start:end]
 assert old.count('XMM_MEM(')==4 and old.count('MEMF(')==3 and old.count('eax = MEM32(esp + 4);')==1
 # Retain the output-pointer fetch at its original position, with its original
 # guest-register state available to any slow-path read. Only take a verified stack fast path.
 fast=old.replace('eax = MEM32(esp + 4);','__builtin_memcpy(&out_va, stack_word, 4); eax = out_va;')
 for reg in ('xmm1','xmm2','xmm3'):fast=fast.replace(reg,'local_'+reg)
 for off in (0,4,8):
  term='eax'+(f' + {off}' if off else '')
  fast=fast.replace(f'MEMF({term})',f'point({off})')
 for off in (0,16,32,48):
  term='ecx'+(f' + 0x{off:X}' if off else '')
  fast=fast.replace(f'XMM_MEM({term})',f'row({off})')
 assert 'XMM_MEM(' not in fast and 'MEMF(' not in fast
 pre="""    uint32_t stack_va=esp+4;
    if ((eax&4095u)+12<=ngb_fast_page_bytes[eax>>12] &&
        (ecx&4095u)+64<=ngb_fast_page_bytes[ecx>>12] &&
        (stack_va&4095u)+4<=ngb_fast_page_bytes[stack_va>>12]) {
        const unsigned char *pt=ngb_fast_ram+(eax&0x7fffffffu), *mt=ngb_fast_ram+(ecx&0x7fffffffu);
        const unsigned char *stack_word=ngb_fast_ram+(stack_va&0x7fffffffu);
        RecompXmm local_xmm1,local_xmm2,local_xmm3; uint32_t out_va;
#define point(offset) __extension__ ({float v;__builtin_memcpy(&v,pt+(offset),4);v;})
#define row(offset) __extension__ ({RecompXmm v;__builtin_memcpy(&v,mt+(offset),16);v;})
"""
 return s[:start]+pre+fast+'    xmm1=local_xmm1; xmm2=local_xmm2; xmm3=local_xmm3;\n#undef point\n#undef row\n    } else {\n'+old+'    }\n'+s[end:]
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('affine-local',[(False,[0])],transform)
