"""Delay two transient XMM0 writes on a callback-free 12-byte coordinate copy."""
from pathlib import Path
import runpy
def transform(s,unit):
    assert unit==28
    i=s.index('void sub_003059A0(void)\n{');j=s.index('\n}',i)
    old=''.join(f'    xmm0 = XMM_SCALAR(MEMF(edx{off})); /* movss */\n    MEMF(0x{0x9501b0+4*n:X}) = xmm0.f[0]; /* movss */\n' for n,off in enumerate(('', ' + 4', ' + 8')))
    assert s[i:j].count(old)==1
    fast='''    if (ngb_fast_ram && edx < NGB_RAM_BYTES-11u && (edx&4095u)+12u<=ngb_fast_page_bytes[edx>>12]) {
        uint32_t bits;
'''
    for n in (0,4,8):
        fast+=f'        __builtin_memcpy(&bits,ngb_fast_ram+edx+{n},4);\n        __builtin_memcpy(ngb_fast_ram+0x{0x9501b0+n:X},&bits,4);\n'
    fast+='        xmm0=(RecompXmm){.u={bits,0,0,0}};\n    } else {\n'+old+'    }\n'
    return s[:i]+s[i:j].replace(old,fast)+s[j:]
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('coord-xmm',[(False,[28])],transform)
