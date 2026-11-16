"""Count actor table roots and indices across both passes, without extra guest reads."""
from pathlib import Path
def transform(s):
 for i,(va,reg) in enumerate([('001CC430','ebx'),('001CC6E0','edi')]):
    k='loc_'+va+': ;';assert s.count(k)==1
    s=s.replace(k,k+f' if(at_on)at_observe({i},{reg},eax);')
 return 'extern unsigned at_on;extern void at_observe(unsigned,unsigned,unsigned);\n'+s
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-actor-table'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'actor-table','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-actor-table/recomp_0016.c').unlink()
