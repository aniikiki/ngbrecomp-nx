"""Count actor table roots and indices across both passes, without extra guest reads."""
from pathlib import Path
def transform(s):
 for i,(fn,anchor,root,key,ptr,kind) in enumerate([
 ('001CBED0','edx = MEM32(eax + 0xC);','edi','ebx','eax','edx'),
 ('001CC4D0','ecx = MEM32(ecx + 0xC);','ebp','edi','ecx','ecx'),
 ('001CC7E0','ecx = MEM32(ecx + 0xC);','edi','ebp','ecx','ecx')]):
    a=s.index('loc_'+fn+': ;');b=s.index('\n}',a);body=s[a:b];assert body.count(anchor)==1
    body=body.replace(anchor,f'unsigned tt_ptr={ptr}; '+anchor+f' if(tt_on)tt_visit({i},{root},{key},tt_ptr,{kind});')
    s=s[:a]+body+s[b:]
 return 'extern unsigned tt_on;extern void tt_visit(unsigned,unsigned,unsigned,unsigned,unsigned);\n'+s
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-tree-triple'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'tree-triple','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-tree-triple/recomp_0016.c').unlink()
