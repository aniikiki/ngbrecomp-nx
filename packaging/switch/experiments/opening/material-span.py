"""Reuse the private ABI's single-load page table in XDK material helpers. Nonlinear aliases retain the bank lookup."""
from pathlib import Path
import runpy
p=Path(__file__).parent
helper='''
static __attribute__((always_inline)) inline void* ms_span(uint32_t va,size_t n){
    if(n<=4096u-(va&4095u) && reg_ends[va>>12])
        return ngb_fast_ram + (va&0x7fffffffu);
    return ngb_ram_span(va,n);
}
'''
def transform(s,u):
 assert u==44
 s=runpy.run_path(str(p/'paired-copy.py'))['transform'](s)
 h=Path('packaging/switch/runtime/direct/material.h').read_text()
 assert h.count('ngb_ram_span(')==12
 h=h.replace('ngb_ram_span(','ms_span(')
 k='#include "recomp_funcs.h"';h=h.replace('#pragma once','').replace(k,k+helper)
 k='#include "direct/material.h"';assert s.count(k)==1
 return s.replace(k,h)
if __name__=='__main__':runpy.run_path(str(p/'model-copy.py'))['build']('material-span',[(False,[44])],transform)
