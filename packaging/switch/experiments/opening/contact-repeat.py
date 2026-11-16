"""Measure exact first-axis inputs on ordinary pages, never replace the query."""
from pathlib import Path
import re,os,sys
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 k='loc_00140D7B: ;'
 assert s.count(k)==1
 code='''
 { uint32_t a=eax+32u, b=esp+48u;
   if(contact_frame && (a&4095u)+20<=ngb_fast_page_bytes[a>>12] && (b&4095u)+4<=ngb_fast_page_bytes[b>>12]){
     uint32_t key[6];
     const unsigned char *ap=ngb_fast_ram+(a&0x7fffffffu);
     __builtin_memcpy(key,ap,4);__builtin_memcpy(key+1,ap+16,4);
     __builtin_memcpy(key+2,ngb_fast_ram+(b&0x7fffffffu),4);
     __builtin_memcpy(key+3,&xmm1,4);__builtin_memcpy(key+4,&xmm3,4);
     __builtin_memcpy(key+5,ngb_fast_ram+0x4149c4,4);
     unsigned i=((eax>>4)*2654435761u)>>20;
     ++contact_n[0];
     if(slots[i].frame==contact_frame && slots[i].va==eax){
       ++contact_n[1]; if(!__builtin_memcmp(key,slots[i].key,sizeof key))++contact_n[2];
     }
     slots[i].frame=contact_frame;slots[i].va=eax;__builtin_memcpy(slots[i].key,key,sizeof key);
   }else if(contact_frame)++contact_n[3]; }
'''
 return 'extern unsigned contact_frame,contact_n[4]; static struct {unsigned frame,va,key[6];} slots[4096];\n'+s.replace(k,k+code),None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[10]').replace('opening-vector-span','opening-contact-repeat'),'contact-repeat-build','exec'))
