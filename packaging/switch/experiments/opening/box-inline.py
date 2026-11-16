"""Inline direct calls within the original ordered point/boxes scan. Never skip side effects or alter the answer."""
from pathlib import Path
import re,os,sys
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 # Keep the public body for indirect entries. The inlined body retains guest
 # stack writes, entry accounting, block polls, early exits and optional outputs.
 start=s.index('void sub_002E4470(void)\n{')
 end=s.index('\n}',start)+2
 body=s[start:end].replace('void sub_002E4470(void)','static inline __attribute__((always_inline)) void box_query_local(void)',1)
 key='RECOMP_ABI_CALL(0x002E4470u, sub_002E4470)'
 assert s.count(key)==3
 anchor='#include <math.h>'
 assert s.count(anchor)==1
 return s.replace(anchor,anchor+'\n'+body).replace(key,'RECOMP_ABI_CALL(0x002E4470u, box_query_local)'),None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[26]').replace('opening-vector-span','opening-box-inline'),'box-reuse-build','exec'))
