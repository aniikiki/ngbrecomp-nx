"""Classify words actually read by each of the three command passes. Never skip side effects or alter the answer."""
from pathlib import Path
import re,os,sys
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 for i,label in enumerate(('00149CF0','00149F41','0014A183')):
    k=f'loc_{label}: ; ngb_guest_block_poll();\n    edx = MEM32(ecx);'
    assert s.count(k)==1
    s=s.replace(k,k+f' if(cmd_frame){{unsigned x=edx-0x90000001u; ++cmd_words[{i}][x<12?x:12];}}')
 return 'extern unsigned cmd_frame,cmd_words[3][13];\n'+s,None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[10]').replace('opening-vector-span','opening-cmd-pass'),'box-reuse-build','exec'))
