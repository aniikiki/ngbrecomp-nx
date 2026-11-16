"""Sample just the search before dispatch or recursion, with paired empty clocks."""
from pathlib import Path
def transform(s):
 a=s.index('void sub_001CC7E0(void)\n{');b=s.index('\n}',a);t=s[a:b]
 k='    ecx = MEM32(eax + 0xC);'; assert t.count(k)==1
 t=t.replace(k,k+"""
    unsigned long long nb_start=0;
    unsigned nb_frame=nb_window;
    if(nb_frame){
        nb_seq++;
        nb_rand=1664525u*nb_rand+1013904223u;
        unsigned mode=nb_rand>>28;
        if(mode==0)nb_start=nb_clock();
        if(mode==1){unsigned long long a=nb_clock();nb_empty+=nb_clock()-a;nb_controls++;}
    }""")
 for k in ['loc_001CC804: ;','loc_001CC830: ;']:
    assert t.count(k)==1;t=t.replace(k,k+' if(nb_start && nb_frame==nb_window){nb_ticks+=nb_clock()-nb_start;nb_samples++;}')
 return 'extern unsigned nb_window,nb_seq,nb_rand,nb_samples,nb_controls;extern unsigned long long nb_clock(void),nb_ticks,nb_empty;\n'+s[:a]+t+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-node-budget'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'node-budget','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-node-budget/recomp_0016.c').unlink()
