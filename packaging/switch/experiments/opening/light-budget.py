"""Sample the generated LightEnable body, excluding its entry checkpoint and surrounding HLE."""
from pathlib import Path
def transform(s):
    a=s.index('loc_003C7850: ;');b=s.index('\n}',a);t=s[a:b]
    k='loc_003C7850: ;'
    t=t.replace(k,k+"""
    unsigned lb_frame=nb_window;
    unsigned long long lb_start=0;
    if(lb_frame){
        nb_seq++;nb_rand=nb_rand*1664525u+1013904223u;
        unsigned mode=nb_rand>>27;
        if(mode==0)lb_start=nb_clock();
        if(mode==1){unsigned long long start=nb_clock();nb_empty+=nb_clock()-start;nb_controls++;}
    }
""")
    k='esp += 8; return;';assert t.count(k)==2
    t=t.replace(k,'esp += 8; if(lb_start && lb_frame==nb_window){nb_ticks+=nb_clock()-lb_start;nb_samples++;} return;')
    return 'extern unsigned nb_window,nb_seq,nb_rand,nb_samples,nb_controls;extern unsigned long long nb_clock(void),nb_ticks,nb_empty;\n'+s[:a]+t+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    src=(p/'page-hot-o3.py').read_text()
    a=src.index('next_set=');b=src.index('parent=d.parent',a)
    src=src[:a]+"d=(base/'core-perf/opening-light-budget').resolve();d.mkdir(exist_ok=True)\n"+src[b:]
    a=src.index('names=');b=src.index('\ns=s[:s.index',a)
    src=src[:a]+"""names=['recomp_0044.c']
(d/names[0]).write_text(transform((base/'gen'/names[0]).read_text()))
"""+src[b:]
    a=src.index('s=s.replace(k," c[-1:');b=src.index('\nexec(compile',a)
    src=src[:a]+'''s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)'''+src[b:]
    exec(compile(src,'tree-level-build','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-light-budget/recomp_0044.c').unlink()
