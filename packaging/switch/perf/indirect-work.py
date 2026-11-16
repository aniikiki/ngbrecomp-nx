"""Profile actual game-core indirect dispatch targets by native ARM call site."""
from pathlib import Path
import subprocess as sp, shlex,json
base=Path('/work/build/switch-runtime')
host=base/'host'; core=base/'core-perf';reg=base/'native-regs';out=core/'indirect';out.mkdir(exist_ok=True)
link=json.loads((core/'exact-link.json').read_text())
link[link.index(str(core/'exact-runtime_test.c.o'))]=str(reg/'host-driver.o')
objs=sorted(reg.glob('recomp_*.c.o'));assert len(objs)==14
for o in objs:
    i=next(i for i,v in enumerate(link) if v.endswith('/'+o.name.replace('.c.o','.o')));link[i]=str(o)
link[1:1]=[str(reg/(n+'.o')) for n in ('entry','gates','checkpoint')]+[str(reg/'backend-host-clip.o')]
cs=sp.check_output(['ninja','-t','commands','ngb-runtime-test'],cwd=host,text=True).splitlines()
cc=next(shlex.split(l) for l in cs if l.endswith('/scene/bridge.c'));orig=Path(cc[-1])
tag='    ++scene_flips;';source=orig.read_text();assert source.count(tag)==1
s=source.replace(tag,tag+' extern void dispatch_window(unsigned); dispatch_window(scene_flips);')
f=out/'bridge.c';f.write_text(s);o=str(f)+'.o';cc[cc.index('-o')+1]=o;cc[cc.index('-MF')+1]=o+'.d';cc[-1]=str(f);cc.insert(1,'-I'+str(orig.parent));sp.run(cc,cwd=host,check=True)
link.insert(1,o)
f=out/'observe.c'
f.write_text("""
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef void (*Fn)(void);
extern Fn __real_recomp_lookup_manual(uint32_t);
struct hit { uintptr_t pc;unsigned va,n; };
static struct hit hits[32768];
static unsigned active,total;
void dispatch_window(unsigned f){
    if(f==1800)active=1;
    if(f!=1920)return;
    active=0;
    for(unsigned i=0;i<32768;++i)if(hits[i].n)
        fprintf(stderr,"[INDIRECT] %lx %08x %u\\n",(unsigned long)hits[i].pc,hits[i].va,hits[i].n);
    fprintf(stderr,"[INDIRECT_TOTAL] %u\\n",total);
}
Fn __wrap_recomp_lookup_manual(uint32_t va){
    if(active){
        uintptr_t pc=(uintptr_t)__builtin_extract_return_addr(__builtin_return_address(0));
        unsigned i=((pc>>3)^((va>>2)*2654435761u))&32767;
        for(unsigned j=0;;++j,i=(i+1)&32767){
            if(j>=32768)abort();
            struct hit *h=hits+i;
            if(!h->n || (h->pc==pc && h->va==va)){h->pc=pc;h->va=va;++h->n;break;}
        }
        ++total;
    }
    return __real_recomp_lookup_manual(va);
}
""")
o=str(f)+'.o';sp.run(['cc','-O2','-c',f,'-o',o],check=True)
link[1:1]=[o,'-Wl,--wrap=recomp_lookup_manual'];link[link.index('-o')+1]=str(out/'replay')
sp.run(link,cwd=host,check=True)
