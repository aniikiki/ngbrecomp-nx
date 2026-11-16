"""Reuse one page check for a candidate's three axis bounds, and one for
the stack coordinates. Preserve early exits, scalar math, volatile order."""
import re,os,sys
from pathlib import Path
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 a=s.index('loc_00140D7B: ;')+len('loc_00140D7B: ;');b=s.index('loc_00140E34: ;',a)
 body=s[a:b];assert not re.search(r'\b(?:RECOMP_|ngb_|PUSH32|POP32)',body)
 labels=re.findall(r'^(loc_[A-F0-9]+):',body,re.M)
 assert all(s.count(label)==body.count(label) for label in labels)
 assert not re.search(r'^\s*(eax|esp)\s*=',body,re.M)
 fast=re.sub(r'^loc_[A-F0-9]+: ;\n','',body,flags=re.M)
 assert all('goto '+label not in fast for label in labels)
 reads=re.findall(r'MEMF\((eax|esp) \+ (0x\w+)\)',fast)
 assert reads and all((0x20 if reg=='eax' else 0x30)<=int(k,16)<=(0x38 if reg=='eax' else 0x38) for reg,k in reads)
 fast=re.sub(r'MEMF\((eax|esp) \+ (0x\w+)\)',lambda m:'(*(volatile float *)('+('axis_obj' if m[1]=='eax' else 'axis_sp')+'+'+str(int(m[2],16)-(0x20 if m[1]=='eax' else 0x30))+'))',fast)
 k="""
    { uint32_t oa=eax+0x20u,sa=esp+0x30u;
      if((oa&4095u)+28<=ngb_fast_page_bytes[oa>>12] && (sa&4095u)+12<=ngb_fast_page_bytes[sa>>12]){
        unsigned char *axis_obj=ngb_fast_ram+(oa&0x7fffffffu), *axis_sp=ngb_fast_ram+(sa&0x7fffffffu);
"""
 return s[:a]+k+fast+'        goto loc_00140E34;\n      }\n    }\n'+body+s[b:],reads
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[10]').replace('opening-vector-span','opening-contact-axis'),'contact-axis-build','exec'))
