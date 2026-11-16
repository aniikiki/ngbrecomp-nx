"""Fuse only direct private void calls followed by a bare AArch64 epilogue."""
from pathlib import Path
import re
# Fixed ABI guest registers x19..x28 survive this native-stack pop.
pat=re.compile(r'^\tbl\s+(ngb_reg_sub_[0-9A-F]+)\n(\tldp\tx29, x30, \[sp\], [0-9]+\n(?:\t\.cfi_(?:remember_state|restore (?:29|30)|def_cfa_offset 0)\n)*)\tret\n',re.M)
def fuse(asm):
    return pat.subn(lambda m:m[2]+'\tb\t'+m[1]+'\n',asm)
if __name__=='__main__':
    base=Path('build/switch-runtime')
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text()
    a=s.index("d=(base/");b=s.index('parent=d.parent',a)
    s=s[:a]+"d=(base/'core-perf/opening-private-tail').resolve();d.mkdir(exist_ok=True)\n"+s[b:]
    k="exec(compile((abi/'gates.py').read_text(),'page-o3-gates','exec'),{})"
    assert s.count(k)==1
    s=s.replace(k,"""g=(abi/'gates.py').read_text()
mark=" dst=out/(obj.stem+'.gated.s')"
assert g.count(mark)==1
g=g.replace(mark," s,count=fuse(s);print(obj.name,'tail branches',count,flush=True)\\n"+mark)
exec(compile(g,'private-tail-gates','exec'),{'fuse':fuse})""")
    exec(compile(s,'private-tail-build','exec'),{'fuse':fuse})
