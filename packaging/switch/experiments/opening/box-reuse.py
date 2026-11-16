"""Observe point/box query reuse. Never skip side effects or alter the answer."""
from pathlib import Path
import re,os,sys
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 k='loc_002E4489: ;';assert s.count(k)==1
 code='''
 if(box_frame){
    ++box_n[0];
    if((eax&4095u)+12<=ngb_fast_page_bytes[eax>>12] &&
       (edx&4095u)+0x9c<=ngb_fast_page_bytes[edx>>12]){
      const unsigned char *pt=ngb_fast_ram+(eax&0x7fffffffu),*b=ngb_fast_ram+(edx&0x7fffffffu);
      const unsigned i=((edx>>2)*2654435761u)>>20;
      unsigned char key[72];__builtin_memcpy(key,b+0x40,48);
      __builtin_memcpy(key+48,b+0x80,12);__builtin_memcpy(key+60,b+0x90,12);
      ++box_n[1];
      if(box_slots[i].frame==box_frame && box_slots[i].va==edx){
        ++box_n[2];unsigned same=!__builtin_memcmp(box_slots[i].shape,key,72);
        box_n[3]+=same;box_n[4]+=same&&!__builtin_memcmp(box_slots[i].point,pt,12);
      }
      box_slots[i].frame=box_frame;box_slots[i].va=edx;
      __builtin_memcpy(box_slots[i].shape,key,72);__builtin_memcpy(box_slots[i].point,pt,12);
    }
 }
'''
 return 'extern unsigned box_frame,box_n[5];static struct {unsigned va,frame;unsigned char shape[72],point[12];} box_slots[4096];\n'+s.replace(k,k+code),None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[26]').replace('opening-vector-span','opening-box-reuse'),'box-reuse-build','exec'))
