"""Time the retained 37A5C5 body without enabling any matrix candidate."""
from pathlib import Path
def transform(s):return s
def guest(s,va='0037A5C5',returns=1):
 k='loc_'+va+': ;'
 a=s.index(k);b=s.index('\n}',a)
 t=s[a:b]; assert t.count('return;')==returns
 t=t.replace(k,k+"""
    unsigned mb_f=mb_frame,mb_selected=0,mb_blank=0;
    unsigned long long mb_start=0;
    if(mb_f){mb_calls++;mb_rng=1664525u*mb_rng+1013904223u;
     unsigned r=mb_rng>>26;mb_selected=r==0;mb_blank=r==1;
     if(mb_blank){unsigned long long start=mb_clock();mb_empty+=mb_clock()-start;mb_controls++;}
     if(mb_selected)mb_start=mb_clock();}
""")
 t=t.replace('return;',"""if(mb_selected){unsigned long long dt=mb_clock()-mb_start;
 if(mb_f==mb_frame){mb_ticks+=dt;mb_n++;}else mb_cross++;}return;""")
 return 'extern unsigned mb_frame,mb_calls,mb_rng,mb_controls,mb_cross,mb_n;extern unsigned long long mb_clock(void),mb_ticks,mb_empty;\n'+s[:a]+t+s[b:]
if __name__=='__main__':
    import sys
    contact='--contact-budget' in sys.argv
    tag='contact-budget' if contact else 'matrix-budget'
    unit=10 if contact else 39
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'",f"d=d.parent/'opening-{tag}'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+f"names=['recomp_{unit:04}.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(guest((base/'gen'/name).read_text()))
 (d/'arm_math.h').write_text(transform(Path('packaging/switch/runtime/arm_math.h').read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'matrix-budget','exec'),{'transform':transform,'guest':(lambda s:guest(s,'00140AF0',4)) if contact else guest})
    for f in Path(f'build/switch-runtime/core-perf/opening-{tag}').glob('recomp_*.c'):f.unlink()
