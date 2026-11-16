"""Fold per-row finite tests into one lane reduction for the two live
ngb_arm_transform calls. Guest RAM checks and math remain the original ones."""
from pathlib import Path
import re,os,sys
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def header():
 s=(p.parents[1]/'runtime/arm_math.h').read_text()
 a=s.index('    if (!isfinite(xyz[0])');b=s.index('    float32x4_t x =',a)
 assert s[a:b].count('ngb_arm_finite')==4
 return s[:a]+'''    if (!isfinite(xyz[0]) || !isfinite(xyz[1]) || !isfinite(xyz[2])) return false;
    // Clearing signs before taking unsigned maxima preserves the infinity
    // threshold for either sign, including every NaN payload.
    uint32x4_t mask=vdupq_n_u32(0x7fffffffu);
    uint32x4_t m0=vandq_u32(vreinterpretq_u32_f32(rows[0]),mask);
    uint32x4_t m1=vandq_u32(vreinterpretq_u32_f32(rows[1]),mask);
    uint32x4_t m2=vandq_u32(vreinterpretq_u32_f32(rows[2]),mask);
    if(translate)m2=vmaxq_u32(m2,vandq_u32(vreinterpretq_u32_f32(rows[3]),mask));
    if(vmaxvq_u32(vmaxq_u32(vmaxq_u32(m0,m1),m2))>=0x7f800000u)return false;
'''+s[b:]
def transform(s):
 k='#include "arm_math.h"';assert s.count(k)==1
 return s.replace(k,header().replace('#pragma once','',1)),None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[10,28]').replace('opening-vector-span','opening-transform-guard'),'transform-guard-build','exec'))
