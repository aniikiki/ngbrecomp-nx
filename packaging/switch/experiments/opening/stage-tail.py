"""Fuse the unchanged contiguous stage defaults and parameter at 30BB81.
No texture bind, per-draw shadow, or state retained across guest calls."""
from pathlib import Path
import os,sys,re
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 k='loc_0030BB81: ;';assert s.count(k)==1
 a=s.index(k);z=s.index('loc_0030BC30: ;',a);old=s[a:z]
 assert old.count('PUSH32(esp, ebp)')==1 and old.count('POP32(esp, ebp)')==1 and 'ngb_guest_block_poll' not in old and 'RECOMP_ABI_CALL' not in old
 code=r'''
    {
      uint32_t arg=edi+0x30u,sw=esp-4u,po=sw&0x7fffffffu,pa=arg&0x7fffffffu;
      if(esi<4 && eax==(esi<<7) && !(sw&3u) && (sw&4095u)+4<=ngb_fast_page_bytes[sw>>12] &&
         (arg&4095u)+4<=ngb_fast_page_bytes[arg>>12] &&
         (po>=0x1000000u || po<0x8000u) && ((uint32_t)(po-pa+3u)>6u)){
        uint32_t fields[4],v;
        __builtin_memcpy(fields,ngb_fast_ram+0x977984u+eax,16);
        __builtin_memcpy(&v,ngb_fast_ram+pa,4);
        if(fields[0]==2 && fields[1]==2 && fields[2]==1 && fields[3]==v){
          PUSH32(esp,ebp);POP32(esp,ebp);
          ecx=2;ebx=1;edx=v;
          goto loc_0030BC30;
        }
      }
    }
'''
 return s.replace(k,k+code),None
src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
exec(compile('if True:'+src.replace('units=[16,28,29]','units=[28]').replace('opening-vector-span','opening-stage-tail'),'stage-tail-build','exec'))
