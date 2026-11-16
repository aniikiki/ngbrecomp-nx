"""Package tested host stage boundaries with low-rate device sampling and compact SD logging.
Before running, run index-ledger.py on the host to materialize its three instrumentation sources.
"""
from pathlib import Path
import shlex,subprocess as sp,tempfile,gzip,struct,hashlib
base=Path('/work/build/switch-runtime');b=base/'switch';reg=base/'native-regs'
root=Path('/work/packaging/switch/runtime');diag=base/'core-perf/opening-index-ledger'
version='0.52.3-diag';out=base/'history'/version;out.mkdir(exist_ok=True)
sdk=Path('/opt/devkitpro');commands=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=b,text=True).splitlines()
link=shlex.split(commands[-1].split('&&')[1])
def once(s,k,v):assert s.count(k)==1,k;return s.replace(k,v)
with tempfile.TemporaryDirectory(dir=out) as tmp:
 d=Path(tmp)
 def comp(name,s,flags=[]):
  c=next(shlex.split(l) for l in commands if l.endswith('/'+name));orig=Path(c[-1]);f=d/orig.name;f.write_text(s);o=str(f)+'.o';old=c[c.index('-o')+1];c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[1:1]=['-I'+str(orig.parent),*flags];c[-1]=str(f);sp.run(c,cwd=b,check=True)
  if old in link:link[link.index(old)]=o
  else:link.insert(1,o)
 s=(diag/'hooks.c').read_text()
 # Linux uses the virtual counter; Horizon/libnx uses the physical system tick.
 s='#include <switch/arm/counter.h>\n'+s
 s=once(s,'uint64_t t;__asm__ volatile("isb; mrs %0,cntvct_el0":"=r"(t)::"memory");return t;', '__asm__ volatile("isb":::"memory");return armGetSystemTick();')
 s=once(s,'uint64_t freq;__asm__("mrs %0,cntfrq_el0":"=r"(freq));','uint64_t freq=armGetSystemTickFreq();')
 assert 'cntvct_el0' not in s

 a=s.index(' fprintf(stderr,"[INDEX_LEDGER]');z=s.index('if(sum!=ix_wall)abort();',a)
 s=s[:a]+r''' char line[512];int used=snprintf(line,sizeof line,"3D scene [INDEX_LEDGER] %u %llu %u %u %u %u %llu",f,(unsigned long long)freq,ix_calls,ix_taken,ix_nested,ix_cross,(unsigned long long)ix_wall);
 for(unsigned i=0;i<10;i++){sum+=ix_ns[i];used+=snprintf(line+used,sizeof line-used," %llu",(unsigned long long)ix_ns[i]);}
 uint64_t v=0;for(unsigned i=0;i<1024;i++){uint64_t t=ix_now();v+=ix_now()-t;}
 snprintf(line+used,sizeof line-used," cal1024=%llu",(unsigned long long)v);ngb_kernel_log(line);'''+s[z:]
 comp('direct/hooks.c',s)
 for name in ['hle.cpp','gpu/threaded.cpp','scene/bridge.c']:comp(name,(diag/Path(name).name).read_text())
 for name in ['runtime.c','main.c']:
  s=(root/name).read_text();assert '0.51.0-rc1' in s;comp(name,s.replace('0.51.0-rc1',version),['-DNGB_REGISTER_PACKAGE','-DNGB_RIGID_CLIP'])
 regs=sorted(reg.glob('recomp_*.c.o'));assert len(regs)==14
 for obj in regs:
  idx=next(i for i,v in enumerate(link) if v.endswith('/'+obj.name.replace('.c.o','.o')));link[idx]=str(obj)
 link[1:1]=[str(reg/(k+'.o')) for k in ('entry','gates','checkpoint','backend-clip')]
 elf=d/'idx.elf';link[link.index('-o')+1]=str(elf);sp.run(link,cwd=b,check=True)
 nm=sp.check_output([sdk/'devkitA64/bin/aarch64-none-elf-nm','-n','-S',elf]);assert b' T ix_stage\n' in nm
 (out/'symbols.gz').write_bytes(gzip.compress(nm,mtime=0))
 nacp=d/'index.nacp';nro=out/'ngb-startup.nro'
 sp.run([sdk/'tools/bin/nacptool','--create','NGB Startup','NGB port development',version,nacp],check=True)
 sp.run([sdk/'tools/bin/elf2nro',elf,nro,'--nacp='+str(nacp),'--icon='+str(sdk/'libnx/default_icon.jpg'),'--romfsdir='+str(base/'romfs')],check=True)
 def digest(p,slot):
  with p.open('rb') as f:
   f.seek(0x18);baseoff=int.from_bytes(f.read(4),'little');f.seek(baseoff);assert f.read(4)==b'ASET';f.seek(baseoff+8+16*slot);pos,n=struct.unpack('<QQ',f.read(16));f.seek(baseoff+pos);h=hashlib.sha256()
   while n:
    buf=f.read(min(1<<20,n));assert buf;h.update(buf);n-=len(buf)
   return h.digest()
 assert digest(nro,1)==hashlib.sha256(nacp.read_bytes()).digest() and digest(nro,2)==digest(base/'history/0.52.1-diag/ngb-startup.nro',2)
 print('verified',version,nro.stat().st_size)
