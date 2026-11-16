"""Count actor table roots and indices across both passes, without extra guest reads."""
from pathlib import Path
def transform(s):
 for i,(ret,fn) in enumerate([('001CC4BA','001CC4D0'),('001CC7BB','001CC7E0')]):
    anchor=f'PUSH32(esp, 0x{ret}u); RECOMP_ABI_CALL(0x{fn}u, sub_{fn});'
    assert s.count(anchor)==1
    s=s.replace(anchor,'{ unsigned frame=tree_epoch; unsigned long long t=tree_begin('+str(i)+'); '+anchor+' if(t)tree_end('+str(i)+',frame,t); }')
 return 'extern unsigned tree_epoch;extern unsigned long long tree_begin(unsigned);extern void tree_end(unsigned,unsigned,unsigned long long);\n'+s
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-tree-pair-cost'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'tree-pair-cost','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-tree-pair-cost/recomp_0016.c').unlink()
