"""Use a single unsigned exponent interval to prove the ordinary float path.
This is a range guard, not integer emulation of rounding. Keep the original
float casts (including FP status) and reference for edge exponents."""
from pathlib import Path
import os,sys,re
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 k='#include "recomp_funcs.h"'
 assert s.count(k)==1
 return s.replace(k,k+'\n'+(p/'round-range.inc').read_text()),None
src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
exec(compile('if True:'+src.replace('units=[16,28,29]','units=[0,8,29,44]').replace('opening-vector-span','opening-round-range'),'round-range-build','exec'))
