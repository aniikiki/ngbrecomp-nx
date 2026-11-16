"""Per-thread lazily resolved ordinary RAM pointers. Cache read/write pointer
by full guest page and job generation; write upgrades *both* physical aliases
while retaining separate permission lengths. No worker reads live guest RAM."""
from pathlib import Path
import shlex,subprocess as sp,shutil
b=Path('/work/build/switch-runtime');w=b/'switch';old=b/'opt050/actor-wave-state';d=b/'opt050/actor-pages';d.mkdir(exist_ok=True)
for f in old.glob('*.h'):shutil.copy(f,d/f.name)
for f in old.glob('*.inc'):shutil.copy(f,d/f.name)
s=(old/'actor.c').read_text();k='ac.trace=trace;ac.events=0;'
s=s.replace(k,k+' if(!++generation){__builtin_memset(resolved,0,sizeof resolved);generation=1;}')
(d/'actor.c').write_text(s)
p=d/'guest_memory.h';s=p.read_text();a=s.index('static inline void *actor_page(');b0=s.index('#define ACTOR_R8',a)
prefix='''struct mapping{unsigned char *ptr;uint32_t tag;uint16_t gen,len;};
static _Thread_local uint16_t generation;
static _Thread_local struct mapping resolved[1024];
static inline void *actor_cached(unsigned a,size_t n,int write){
 unsigned pg=a>>12,phys=pg&0x7ffff,off=a&4095;struct mapping *m=&resolved[(pg^(pg>>9))&1023];
 if(m->tag==pg && m->gen==generation && n<=m->len && off<=m->len-n && (!write||ac.index[phys]))return m->ptr+off;
 if(phys>=32768 || off+n>4096 || ac.pages[pg]<off+n)actor_bail(a);
 ac.foot[phys]=1;unsigned slot=ac.index[phys];
 if(write&&!slot){if(ac.used>=512)actor_bail(0xf0000001u);slot=++ac.used;ac.index[phys]=slot;ac.touched[slot-1]=phys;
   __builtin_memcpy(ac.slots+(slot-1)*4096,ac.ram+phys*4096,4096);
   unsigned alias=pg^0x80000;struct mapping *other=&resolved[(alias^(alias>>9))&1023];
   if(other->tag==alias)other->gen=0;
 }
 m->ptr=slot?ac.slots+(slot-1)*4096:ac.ram+phys*4096;m->gen=generation;m->tag=pg;m->len=ac.pages[pg];return m->ptr+off;
}
static inline void *actor_page(unsigned a,size_t n){return actor_cached(a,n,1);}
static inline const void *actor_read_page(unsigned a,size_t n){return actor_cached(a,n,0);}
'''
p.write_text(s[:a]+prefix+s[b0:])
cmd=next(shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines() if x.endswith('/recomp_0010.c'))
o=str(d/'footprint.o');cmd[cmd.index('-o')+1]=o;cmd[cmd.index('-MF')+1]=o+'.d';cmd[-1]=str(d/'actor.c');cmd[1:1]=['-I'+str(d)];cmd.insert(-1,'-g0');sp.run(cmd,cwd=w,check=True)
