"""Specialize only the no-child recursive call with no service due and an ordinary stack."""
from pathlib import Path
import runpy
p=Path(__file__).parent
helper=runpy.run_path(str(p/'empty-material.py'))['helper'].replace('empty_material','tree_empty_child').replace('0x30c240','0x308d50').replace('(lo&4095u)+8u','(lo&4095u)+12u').replace(' q[1]=ret;', ' if(q[2])return 0;\n q[1]=ret;')
def transform(s):
    key='PUSH32(esp, 0x00308D69u); RECOMP_ABI_CALL(0x00308D50u, sub_00308D50);'
    assert s.count(key)==1
    return s.replace('#include "recomp_funcs.h"','#include "recomp_funcs.h"\n'+helper).replace(key,'if(!tree_empty_child(0x00308D69u)){ '+key+' }')
if __name__=='__main__':
    s=(p/'tree-level.py').read_text().split("if __name__=='__main__':",1)[1]
    exec(compile('if True:'+s.replace('opening-tree-level','opening-tree-null'),'tree-null-build','exec'))
