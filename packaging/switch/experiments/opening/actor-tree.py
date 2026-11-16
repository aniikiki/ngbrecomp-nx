"""Count actor table roots and indices across both passes, without extra guest reads."""
from pathlib import Path
def transform(s):
 for i,(fn,anchor,root,key) in enumerate([('001CC4D0','edi = MEM32(esp + 0x10);','ebp','edi'),('001CC7E0','edi = MEM32(esp + 0x10);','edi','ebp')]):
    a=s.index('loc_'+fn+': ;');b=s.index('\n}',a);body=s[a:b];assert body.count(anchor)==1
    s=s[:a]+body.replace(anchor,anchor+f' if(at_on)at_visit({i},{root},{key});')+s[b:]
 return 'extern unsigned at_on;extern void at_visit(unsigned,unsigned,unsigned);\n'+s
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-actor-tree'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'actor-tree','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-actor-tree/recomp_0016.c').unlink()
