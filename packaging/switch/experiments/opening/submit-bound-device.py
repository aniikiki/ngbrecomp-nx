"""Measure the upper bound on eliminating Draw submission with unchanged work on hardware.
"""
from pathlib import Path
import shlex,subprocess as sp,tempfile,gzip,struct,hashlib
base=Path('/work/build/switch-runtime');b=base/'switch';reg=base/'native-regs'
root=Path('/work/packaging/switch/runtime');diag=base/'core-perf/opening-index-ledger'
import sys
wide='--wide' in sys.argv
version=('0.55.5-hold' if '--hold' in sys.argv else '0.55.4-cg' if '--cg' in sys.argv else '0.55.3-save' if '--save' in sys.argv else '0.55.2-movie' if '--movie' in sys.argv else '0.55.1-pad' if '--pad' in sys.argv else '0.55.0-sd') if wide else '0.53.0-bound';out=base/'history'/version;out.mkdir(exist_ok=True)
sdk=Path('/opt/devkitpro');commands=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=b,text=True).splitlines()
link=shlex.split(commands[-1].split('&&')[1])
def once(s,k,v):assert s.count(k)==1,k;return s.replace(k,v)
with tempfile.TemporaryDirectory(dir=out) as tmp:
 d=Path(tmp)
 def comp(name,s,flags=[]):
  c=next(shlex.split(l) for l in commands if l.endswith('/'+name));orig=Path(c[-1]);f=d/orig.name;f.write_text(s);o=str(f)+'.o';old=c[c.index('-o')+1];c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[1:1]=['-I'+str(orig.parent),*flags];c[-1]=str(f);sp.run(c,cwd=b,check=True)
  if old in link:link[link.index(old)]=o
  else:link.insert(1,o)
 # Real output and guest semantics are preserved. Time exactly the candidate
 # span on every draw; combine with thread ticks already recorded by main.c.
 s=(Path('/work/src/d3d/hle.cpp')).read_text()
 s='#include <switch/arm/counter.h>\nextern "C" {extern unsigned bd_on;extern unsigned long long bd_ticks;extern unsigned bd_draws;}\n'+s
 k="    if (!g_backend) return;\n    bool measure"
 s=once(s,k,"    if (!g_backend) return;\n    auto bd_start=bd_on?armGetSystemTick():0;\n    bool measure")
 k="    if (measure) ngb_direct_draw_time"
 s=once(s,k,"    if(bd_start){bd_ticks+=armGetSystemTick()-bd_start;++bd_draws;}\n"+k)
 if wide:
  swap='        if (g_backend) g_backend->Present(g_state.rt);'
  s='extern "C" void bd_present_mark(void);\n'+once(s,swap,'        if (g_backend) { bd_present_mark(); g_backend->Present(g_state.rt); }')
 comp('hle.cpp',s)
 s=(root/'scene/bridge.c').read_text()
 k='static void record_flip(void)'
 s=once(s,k,r"""unsigned bd_on,bd_draws;unsigned long long bd_ticks;
extern unsigned long long bd_thread_ticks(unsigned *error);
static unsigned long long bd_by_frame[121],bd_cp[121];static unsigned bd_count[121],bd_err;static unsigned long long lastcpu;
static void bd_boundary(unsigned f){
 if(f>=30 && f<=120){unsigned long long cpu=bd_thread_ticks(&bd_err);bd_cp[f]=cpu-lastcpu;lastcpu=cpu;}
 if(bd_on && f<=120){bd_by_frame[f]=bd_ticks;bd_count[f]=bd_draws;}
 bd_on=f>=30 && f<120;bd_ticks=0;bd_draws=0;
 if(f==121){char line[128];
 for(unsigned j=31;j<=120;j++){snprintf(line,sizeof line,"3D scene [DRAW_BOUND] frame=%u draws=%u ticks=%llu cpu=%llu rc=%u",j,bd_count[j],bd_by_frame[j],bd_cp[j],bd_err);ngb_kernel_log(line);}}
}
"""+k)
 s=once(s,'    ++scene_flips;','    ++scene_flips; bd_boundary(scene_flips);')
 s=once(s,'            ngb_direct_reset_stats();','            ngb_direct_reset_stats(); bd_boundary(0);')
 if wide:
  s=once(s,'static void bd_boundary(unsigned f){','''unsigned bd_present_seq;
static unsigned bd_last_present,bd_present_delta[121];
static unsigned bd_first_draw,bd_last_draw,bd_seen_present;
static unsigned bd_split[121][2];
void bd_present_mark(void){
 ++bd_present_seq;
 if(bd_on){if(!bd_seen_present)bd_first_draw=bd_draws;bd_last_draw=bd_draws;bd_seen_present=1;}
}
static unsigned long long bd_flip_ns[121];
static void bd_boundary(unsigned f){
 if(bd_on && f<=120){
  bd_split[f][0]=bd_first_draw;bd_split[f][1]=bd_last_draw;
 }
 bd_first_draw=bd_last_draw=bd_seen_present=0;
 if(f==0)bd_last_present=bd_present_seq;
 if(f>0 && f<=120){
  bd_flip_ns[f]=intervals[f-1-window_flip];
  bd_present_delta[f]=bd_present_seq-bd_last_present;bd_last_present=bd_present_seq;
 }
''')
  s=once(s,'if(f>=30 && f<=120)', 'if(f<=120)')
  s=once(s,' for(unsigned j=31;j<=120;j++){snprintf',''' for(unsigned j=1;j<=120;j++){
 snprintf(line,sizeof line,"3D scene [OPEN_FLIP] frame=%u wall_ns=%llu cpu_ticks=%llu presents=%u rc=%u",
 j,bd_flip_ns[j],bd_cp[j],bd_present_delta[j],bd_err);ngb_kernel_log(line);}
 for(unsigned j=31;j<=120;j++){snprintf''')
  s=once(s,'cpu=%llu rc=%u",j,bd_count[j],bd_by_frame[j],bd_cp[j],bd_err','cpu=%llu rc=%u first_draw=%u last_draw=%u",j,bd_count[j],bd_by_frame[j],bd_cp[j],bd_err,bd_split[j][0],bd_split[j][1]')
 comp('scene/bridge.c',s)
 if '--check-opening-counters' in sys.argv:
  assert wide
  counters=s[s.index('unsigned bd_on,bd_draws;'):s.index('static void record_flip(void)')]
  test=d/'check.c';test.write_text('#include <stdio.h>\n#include <assert.h>\nstatic unsigned window_flip,lines;static unsigned long long intervals[120];void ngb_kernel_log(const char*p){++lines;} unsigned long long bd_thread_ticks(unsigned*p){return 1;}\n'+counters+'''
int main(void){for(int pass=0;pass<2;pass++){
 window_flip=0;bd_boundary(0);
 for(unsigned f=1;f<=121;f++){
  if(f==31 && !pass){bd_draws=3;bd_present_mark();bd_draws=6;bd_present_mark();bd_draws=9;}
  if(f==32){bd_present_mark();bd_draws=5;}
  if(f==33){bd_draws=7;bd_present_mark();}
  bd_boundary(f);if(f==30)window_flip=30;
  if(f<121)assert(lines==pass*210);
 }
 assert(lines==(pass+1)*210);
 assert(bd_count[31]==(pass?0:9) && bd_present_delta[31]==(pass?0:2));
 assert(bd_split[31][0]==(pass?0:3) && bd_split[31][1]==(pass?0:6));
 assert(bd_present_delta[32]==1 && bd_split[32][0]==0 && bd_split[32][1]==0);
 assert(bd_present_delta[33]==1 && bd_split[33][0]==7 && bd_split[33][1]==7);
}return 0;}
''')
  sp.run(['cc','-std=c11',test,'-o',d/'check'],check=True);sp.run([d/'check'],check=True)
  print('verified two-scene counter replay, deferred output and Horizon target objects');sys.exit(0)
 if '--cg' in sys.argv: comp('ohci_boot.c',(root/'ohci_boot.c').read_text())
 if '--movie' in sys.argv: comp('pgraph_boot.c',(root/'pgraph_boot.c').read_text())
 if wide:
  for name in ['scanout.c','identity.c','files.c','opening_movie.c']:comp(name,(root/name).read_text())
 for name in ['runtime.c','main.c']:
  s=(root/name).read_text()
  if name=='main.c':s+='\nunsigned long long bd_thread_ticks(unsigned *error){u64 value=0;*error|=thread_ticks(threadGetSelf()->handle,&value);return value;}\n'
  assert '0.51.0-rc1' in s;comp(name,s.replace('0.51.0-rc1',version),['-DNGB_REGISTER_PACKAGE','-DNGB_RIGID_CLIP'])
 regs=sorted(reg.glob('recomp_*.c.o'));assert len(regs)==14
 for obj in regs:
  idx=next(i for i,v in enumerate(link) if v.endswith('/'+obj.name.replace('.c.o','.o')));link[idx]=str(obj)
 link[1:1]=[str(reg/(k+'.o')) for k in ('entry','gates','checkpoint','backend-clip')]
 elf=d/'idx.elf';link[link.index('-o')+1]=str(elf);sp.run(link,cwd=b,check=True)
 nm=sp.check_output([sdk/'devkitA64/bin/aarch64-none-elf-nm','-n','-S',elf]);assert b' bd_ticks\n' in nm
 (out/'symbols.gz').write_bytes(gzip.compress(nm,mtime=0))
 nacp=d/'index.nacp';nro=out/'ngb-startup.nro'
 sp.run([sdk/'tools/bin/nacptool','--create','NGB Startup','NGB port development',version,nacp],check=True)
 romfs=base/'romfs'
 if wide:
  import shutil
  romfs=d/'program-romfs';romfs.mkdir()
  shutil.copyfile(base/'romfs/.ngb-spirv',romfs/'.ngb-spirv')
 sp.run([sdk/'tools/bin/elf2nro',elf,nro,'--nacp='+str(nacp),'--icon='+str(sdk/'libnx/default_icon.jpg'),'--romfsdir='+str(romfs)],check=True)
 def digest(p,slot):
  with p.open('rb') as f:
   f.seek(0x18);baseoff=int.from_bytes(f.read(4),'little');f.seek(baseoff);assert f.read(4)==b'ASET';f.seek(baseoff+8+16*slot);pos,n=struct.unpack('<QQ',f.read(16));f.seek(baseoff+pos);h=hashlib.sha256()
   while n:
    buf=f.read(min(1<<20,n));assert buf;h.update(buf);n-=len(buf)
   return h.digest()
 assert digest(nro,1)==hashlib.sha256(nacp.read_bytes()).digest()
 if wide:
  assert [x.name for x in romfs.iterdir()]==['.ngb-spirv']
  with nro.open('rb') as f:
   f.seek(0x18);asset=int.from_bytes(f.read(4),'little')
   f.seek(asset+8+16*2);offset,size=struct.unpack('<QQ',f.read(16))
   assert (romfs/'.ngb-spirv').stat().st_size<=size<(romfs/'.ngb-spirv').stat().st_size+65536
 else: assert digest(nro,2)==digest(base/'history/0.52.1-diag/ngb-startup.nro',2)
 print('verified',version,nro.stat().st_size)
