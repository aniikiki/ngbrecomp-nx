"""Only recompile units which dominate observed entries to functions containing
FIST. Reuse the full-domain single/multi-unit cross-build used by vector-span."""
from pathlib import Path
import runpy
p=Path(__file__).resolve().parent
src=(p/'vector-span.py').read_text()
src=src[src.index("if __name__=='__main__':"):]
src=src.replace('units=[16,28,29]','units=[1,16,37,44]').replace('opening-vector-span','opening-fist-round')
import os,sys,re
base=Path('build/switch-runtime')
def transform(s):
 k='#include "recomp_funcs.h"'
 assert s.count(k)==1 and 'recomp_fist(' in s
 return (s.replace('recomp_fist(','ngb_arm_fist(').replace(k,k+'\n'+(p/'fist-round.inc').read_text()),None)
assert '--build' in sys.argv
exec(compile(src,'fist-round-build','exec'))
