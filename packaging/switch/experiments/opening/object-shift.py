"""Keep all scalar subtractions, original order and XMM writes; share the page check."""
from pathlib import Path
import re,runpy
def transform(s,u):
 a=s.index('void sub_00035F60(void)\n{');b=s.index('\n}',a)
 count=[]
 def group(m):
    body=m[0]
    def addr(x):
        off=int(x[1] or 0,0) if x[1] else 0
        return '(*(volatile float *)(shift_ptr+'+str(off+8)+'))'
    pat=r'MEMF\(eax(?: \+ (-?(?:0x[0-9A-F]+|\d+)))?\)'
    offsets=[int(v or '0',0) for v in re.findall(pat,body)]
    assert offsets[::2]==offsets[1::2] and min(offsets)==-8
    n=max(offsets)+12; count.append(n)
    check=''.join(f'if ((uintptr_t)&MEMF(eax+({i})) != (uintptr_t)(shift_ptr+{i+8})) __builtin_trap();' for i in sorted(set(offsets)))
    return ('    { uint32_t base=eax-8; static int mode=-1; if(mode<0)mode=getenv("NGB_SHIFT_CHECK")?2:getenv("NGB_SHIFT_ON")?1:0; '
            f'if(mode && !(base&3u) && base>=4096 && base<0x04000000u && (base&4095u)+{n}u<=ngb_fast_page_bytes[base>>12]){{ unsigned char *shift_ptr=ngb_fast_ram+base; '
            +'if(mode==2){static unsigned hits;'+check+'if(++hits==1)puts("[SHIFT_CHECK] bytes='+str(n)+'");}\n'
            +re.sub(pat,addr,body)+'}else{\n'+body+'}}\n')
 body=re.sub(r'(?:    xmm3 = XMM_SCALAR\(MEMF\(eax[^\n]+\n    xmm3\.f\[0\] = [^\n]+\n    MEMF\(eax[^\n]+\n)+',group,s[a:b])
 assert count==[236,44]
 return '#include <stdlib.h>\n#include <stdio.h>\n'+s[:a]+body+s[b:]
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('object-shift',[(False,[1])],transform)
