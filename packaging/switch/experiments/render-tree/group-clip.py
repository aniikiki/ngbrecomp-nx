"""Attribute renderer clip verdicts to ordered callbacks, not individual meshes.
Offline only. Count every draw emitted by each callback, including draws outside
a mesh; unmatched classifications invalidate the cost estimate."""
from pathlib import Path
import sys,shlex,subprocess as sp
w=Path('/work');base=w/'build/switch-runtime';perf=w/'packaging/switch/perf'
out=base/'core-perf/group-clip';out.mkdir(exist_ok=True)
if sys.argv[1]=='cross':
    s=(base/'gen/recomp_0028.c').read_text()
    for site in ('00308D20','00308D6C'):
        k='RECOMP_ICALL_SAFE_AT(_icall_target, _icall_esp, 0x'+site+'u);'
        assert s.count(k)==1
        s=s.replace(k,'unsigned marker=gc_enter(_icall_target); '+k+' gc_leave(marker);')
    f=out/'recomp_0028.c';f.write_text('unsigned gc_enter(unsigned);void gc_leave(unsigned);\n'+s)
    c=next(shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=base/'switch',text=True).splitlines() if x.endswith('/'+f.name))
    o=str(f)+'.o';c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(f);c.insert(-1,'-g0');sp.run(c,cwd=base/'switch',check=True)
else:
    p=perf/'mesh-clip-work.py';s=p.read_text().replace("out=core/'mesh-clip'","out=core/'group-clip'")
    a=s.index("tag='void ngb_direct_mesh_scope");b=s.index("rep('    measured_frames",a)
    s=s[:a]+'''s+="""
#include <time.h>
static unsigned mc_seq,mc_f,mc_n,mc_mesh;
static uint64_t mc_start;
unsigned mc_id,mc_commands;
static FILE *mc_file;
static uint64_t mc_clock(void){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
unsigned gc_enter(unsigned target){
 if(mc_f<1800 || mc_f>=1920 || mc_id)return 0;
 if(!mc_file){mc_file=fopen("/work/build/switch-runtime/core-perf/group-clip/mesh-cost.bin","wb");if(!mc_file)abort();}
 mc_n=mc_f+1;mc_mesh=target;mc_commands=0;mc_start=mc_clock();return mc_id=++mc_seq;
}
void gc_leave(unsigned marker){
 if(!marker)return;
 if(marker!=mc_id)abort();
 uint32_t row[]={marker,mc_n,mc_mesh,mc_commands,(uint32_t)(mc_clock()-mc_start)};
 if(fwrite(row,sizeof(row),1,mc_file)!=1)abort();if(mc_n==1920)fflush(mc_file);mc_id=0;
}
"""
'''+s[b:]
    s=s.replace('core-perf/mesh-draw.bin','core-perf/group-clip/mesh-draw.bin')
    k="link[link.index('-o')+1]"
    s=s.replace(k,"link[next(i for i,v in enumerate(link) if v.endswith('/recomp_0028.o'))]=str(out/'recomp_0028.c.o')\nlink.insert(1,'-Wl,--strip-debug')\n"+k)
    exec(compile(s,str(p),'exec'),{'__file__':str(p)})
