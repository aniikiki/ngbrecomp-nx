"""Turn the existing guarded insertion path into an explicit descent/unwind.
Replay every original entry, stack write, polling point, left/right epilogue.
Fallback (including indirect tails) remains a normal translated function."""
from pathlib import Path
import os
base=Path('/work/build/switch-runtime');d=base/'core-perf/opening-tree-loop';d.mkdir(exist_ok=True)
abi=Path('/work/packaging/switch/arm-registers');rt=abi.parent/'runtime'
s=(base/'gen/recomp_0028.c').read_text()
a=s.index('void sub_00308BF0(void)\n{');b=s.index('\n}',a)+2
t=s[a:b]
entry='    RECOMP_ENTRY(0x00308BF0u);'
assert t.count(entry)==1
t=t.replace(entry,'''    unsigned loop_depth=0, directions=0;
tree_next_level:
'''+entry)
h=(rt/'tree_insert.inc').read_text()
k='                    RECOMP_ABI_CALL(0x00308BF0u, sub_00308BF0);'
assert h.count(k)==1
h=h.replace(k,'''                    if (loop_depth<31 && tree_loop_pick) {
                        directions=(directions<<1)|left;
                        ++loop_depth;
                        goto tree_next_level;
                    }
'''+k)
t=t.replace('#include "tree_insert.inc"',h)
assert t.count('return;')==6,t.count('return;')
t=t.replace('return;', 'goto tree_complete;')
t=t[:-2]+'''
tree_complete:
    if (!loop_depth) return;
    --loop_depth;
    if (directions & 1u) {directions >>= 1;goto loc_00308CAE;}
    directions >>= 1;goto loc_00308C83;
}'''
s='extern unsigned tree_loop_pick;\n'+s[:a]+t+s[b:];(d/'recomp_0028.c').write_text(s)
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text()
s=s.replace(' sp.run(c,cwd=w,check=True)'," c[-1]=str(o/n)\n sp.run(c,cwd=w,check=True)")
s=s.replace('ex.map(build,units)',"ex.map(build,['recomp_0028.c'])")
exec(compile(s,'tree-abi','exec'),{})
exec(compile((abi/'gates.py').read_text(),'tree-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
