"""Reuse existing 14-unit Linux alias experiment; time only original opening frames."""
from pathlib import Path
import subprocess as sp
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup');existing=p.core/'scalar-view'
for orig in sorted(REGS.glob('recomp_*.c.o'))+[REGS/'entry.o',REGS/'gates.o']:
    p.link[p.link.index(str(orig))]=str(existing/('b-'+orig.name))
    p.link.insert(1,str(existing/('a-'+orig.name)))
for name in ['vm.c.o','contiguous.c.o']:
    ix=[i for i,v in enumerate(p.link) if v.endswith('/'+name)]
    if ix:p.link[ix[0]]=str(existing/name)
    else:p.link.insert(1,str(existing/name))
mapping=existing/'mapping.o'
if '--sites' in sys.argv:
    source=(Path(__file__).resolve().parent.parent/'arm-fastmem/scalar-mapping.c').read_text()
    for a,b in [('uintptr_t pc, slow;', 'uintptr_t pc, slow; unsigned count;'),('++buckets[','++sites[lo].count; ++buckets['),
                ('    free(sites);', '    extern char __executable_start; for(size_t i=0;i<nsite;i++)if(sites[i].count)fprintf(stderr,"[SLOW_SITE] %lx %lx %u\\n",(unsigned long)(sites[i].pc-(uintptr_t)&__executable_start),(unsigned long)(sites[i].slow-(uintptr_t)&__executable_start),sites[i].count);\n    free(sites);')]:
        assert source.count(a)==1
        source=source.replace(a,b)
    c=p.out/'opening-map.c';mapping=p.out/'opening-map.o';c.write_text(source)
    sp.run(['cc','-O2','-c',c,'-o',mapping],check=True)
p.link[1:1]=[str(existing/'select.o'),str(mapping),'-Wl,--strip-debug']
# Use today's original host runtime with only the backing allocation replaced.
rt=(REGS/'host-runtime.inc').read_text()
for a,b in [('ram = calloc(1, 2u * RAM_BYTES);','extern void *ngb_alias_create(void);ram=ngb_alias_create();'),('free(ram); ram = NULL;','extern void ngb_alias_destroy(void*);ngb_alias_destroy(ram);ram=NULL;')]:
    assert rt.count(a)==1;rt=rt.replace(a,b)
# Avoid shadowing other probes' ordinary host-runtime.inc in the reusable build dir.
(p.out/'opening-alias.inc').write_text(rt)
driver=(REGS/'host-driver.c').read_text().replace('"host-runtime.inc"','"opening-alias.inc"')
k='void __real_ngb_kernel_log'
driver=driver.replace(k,'''
unsigned trial_variant;
void scalar_frame(unsigned f,unsigned draws){
 static uint64_t last;static unsigned prev;
 struct timespec ts;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&ts);
 uint64_t now=ts.tv_sec*1000000000ull+ts.tv_nsec;
 if(f && last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\\n",f,trial_variant,(unsigned long long)(now-last),draws-prev);
 trial_variant=f<120 && ((((f/2+12345)*2654435761u>>31)^(f&1))^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;prev=draws;
}
'''+k)
obj=p.compile('runtime_test.c',driver,['-I'+str(REGS),'-I'+str(RUNTIME),'-include',str(RUNTIME/'switch_guest_regs.h'),'-DNGB_RIGID_CLIP','-DNGB_REGISTER_PACKAGE'])
p.link[p.link.index(str(p.core/'exact-runtime_test.c.o'))]=obj
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
    assert s.count(k)==1
    s=s.replace(k,k+f' extern void scalar_frame(unsigned,unsigned);scalar_frame({arg},draws);')
p.add('scene/bridge.c',s);p.finish()
