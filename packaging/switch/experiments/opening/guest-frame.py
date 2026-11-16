"""Try compiler-managed frame-pointer omission on five sampled units; keep
all guest calls/checkpoints, x86 frame state and no-sibling-call convention."""
from pathlib import Path
import os,re,sys
base=Path('build/switch-runtime')
p=Path(__file__).resolve().parent
def transform(s):return s,None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 src=src.replace('units=[16,28,29]','units=[0,2,27,28,44]').replace('opening-vector-span','opening-guest-frame')
 src=src.replace("c.insert(-1,'-I/work/build/switch-runtime/gen')","c.insert(-1,'-fomit-frame-pointer');c.insert(-1,'-I/work/build/switch-runtime/gen')")
 exec(compile('if True:'+src,'guest-frame-build','exec'))
