"""Count already-loaded child and callback operands at the actual recursive traversal."""
from pathlib import Path
def transform(s):
    fn='sub_00308D50'
    a=s.index('void '+fn+'(void)\n{');b=s.index('\n}',a)+2
    body=s[a:b]
    k='eax = MEM32(esi + 0xC);'
    assert body.count(k)==1
    body=body.replace(k,k+' if(tree_active){++tree_nodes;tree_nulls+=(eax==0);}')
    k='uint32_t _icall_target = MEM32(esi + 4);'
    assert body.count(k)==1
    body=body.replace(k,k+' if(tree_active){unsigned j=0;while(j<64 && tree_n[j] && tree_va[j]!=_icall_target)++j;if(j==64)++tree_over;else{tree_va[j]=_icall_target;++tree_n[j];}}')
    return 'extern unsigned tree_active,tree_nodes,tree_nulls,tree_over,tree_n[64],tree_va[64];\n'+s[:a]+body+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-tree-census').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0028.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-tree-census/recomp_0028.c').unlink()
