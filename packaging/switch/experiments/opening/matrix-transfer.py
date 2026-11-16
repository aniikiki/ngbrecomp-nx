"""Two original matrix loads into the same fixed live matrix. Resolve the
source once and keep all four old rows even on partial overlap."""
from pathlib import Path
import re,sys,os
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 for fn in ('00305950','003059A0'):
  a=s.index('void sub_'+fn+'(void)\n{');b=s.index('\n}',a);body=s[a:b]
  k='    xmm0 = XMM_MEM(eax);';i=body.index(k);z=body.index(' /* movaps */',body.index('    XMM_STORE(ecx + 0x30'))+len(' /* movaps */')
  old=body[i:z]
  assert old.count('XMM_MEM')==old.count('XMM_STORE')==4
  assert re.search(r'ecx = 0x950180;\s*eax = MEM32\(esp\);\s*$',body[:i])
  path='''    if ((eax&4095u)+64 <= ngb_fast_page_bytes[eax>>12]) {
        const unsigned char *source=ngb_fast_ram+(eax&0x7fffffffu);
        unsigned char *dest=ngb_fast_ram+0x950180;
'''
  for j in range(4):path+=f'        __builtin_memcpy(&xmm{j},source+{16*j},16);\n'
  for j in range(4):path+=f'        __builtin_memcpy(dest+{16*j},&xmm{j},16);\n'
  s=s[:a]+body[:i]+path+'    } else {\n'+old+'\n    }'+body[z:]+s[b:]
 return s,None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[28]').replace('opening-vector-span','opening-matrix-transfer'),'matrix-transfer-build','exec'))
