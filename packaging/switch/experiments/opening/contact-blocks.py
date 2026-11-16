"""Count actual basic-block arrivals in the sampled contact function.
No per-event helper or clock; counters are not performance measurements."""
import re,os,sys
from pathlib import Path
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 a=s.index('void sub_00140AF0(void)\n{');b=s.index('\n}',a)
 body=s[a:b]; labels=[]
 def add(m):
  labels.append(m[1])
  return m[0]+f' ++contact_blocks[{len(labels)-1}];'
 body=re.sub(r'^loc_([0-9A-F]+): ;',add,body,flags=re.M)
 assert len(labels)<256 and '00140FF2' in labels
 return 'extern unsigned contact_blocks[256];\n'+s[:a]+body+s[b:],labels
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[10]').replace('opening-vector-span','opening-contact-blocks'),'contact-block-build','exec'))
