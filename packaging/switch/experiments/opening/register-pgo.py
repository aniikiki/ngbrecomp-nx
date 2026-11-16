"""Link the private register ABI training and timing replays without changing the Switch package."""
from pathlib import Path
import sys,subprocess as sp
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
mode=sys.argv[1];assert mode in ('base','train','use')
p=NativeProbe('opening-register-pgo')
if mode!='base':
 for o in sorted(REGS.glob('recomp_*.c.o'))+[REGS/'gates.o',REGS/'entry.o']:
  p.link[p.link.index(str(o))]=str(p.out/o.name)
train=mode=='train'
if train:
 # Zero the arc arrays at the demo boundary: training excludes boot, movies and menus.
 objs=sorted(p.out.glob('recomp_*.c.o'));reset='';symbols=0
 for unit,o in enumerate(objs):
  rows=sp.check_output(['nm','-S',o],text=True)
  names=[(v[3],int(v[1],16)) for l in rows.splitlines() if len(v:=l.split())==4 and v[3].startswith('__gcov0.')]
  assert names
  # Local GCC labels remain local. Place an in-unit reset routine beside them.
  asm=(p.out/o.name.replace('.o','.gated.s')).read_text()+'\n.text\n'
  fn=f'clear_open_profile_{unit}';asm+=f'.global {fn}\n{fn}:\n'
  for n,size in names:
   assert size%8==0 and 0<size//8<65536
   asm+=f'adrp x9,{n}\nadd x9,x9,:lo12:{n}\nmov x10,#{size//8}\n1: str xzr,[x9],#8\nsubs x10,x10,#1\nb.ne 1b\n'
  asm+='ret\n';q=p.out/'clear.s';q.write_text(asm);sp.run(['cc','-march=armv8-a+crc+crypto','-c',q,'-o',o],check=True);q.unlink();reset+=f'extern void {fn}(void);{fn}();';symbols+=len(names)
 (p.out/'profiles'/str(p.out).lstrip('/')).mkdir(parents=True,exist_ok=True)
 print('clearing arc arrays:',symbols,flush=True)
 o=p.out/'emit.o';sp.run(['cc','-O2','-c',Path(__file__).resolve().parents[2]/'perf/emit.c','-o',o],check=True)
 p.link.insert(1,str(o));p.link.append(str(p.out/'gcov.a'))
else:reset=''
v=(RUNTIME/'scene/bridge.c').read_text()
k='            ngb_direct_reset_stats();';assert v.count(k)==1
v=v.replace(k,k+'extern void pg_frame(unsigned,unsigned);pg_frame(0,draws);'+reset)
k='    ++scene_flips;';assert v.count(k)==1;v=v.replace(k,k+'extern void pg_frame(unsigned,unsigned);pg_frame(scene_flips,draws);')
p.add('scene/bridge.c',v)
k=p.link.index(str(p.core/'exact-runtime_test.c.o'))
o=p.compile('runtime_test.c',(REGS/'host-driver.c').read_text().replace('void __real_ngb_kernel_log',r'''
void pg_frame(unsigned f,unsigned draws){
 static uint64_t init,last;static unsigned prev;struct timespec t;
 clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(!f||!init)init=now;else if(f<=120)fprintf(stderr,"[PGFRAME] %u %llu %u %llu\n",f,(unsigned long long)(now-last),draws-prev,(unsigned long long)(now-init));
 last=now;prev=draws;}
void __real_ngb_kernel_log'''),['-I'+str(REGS),'-I'+str(RUNTIME),'-include',str(RUNTIME/'switch_guest_regs.h'),'-DNGB_RIGID_CLIP','-DNGB_REGISTER_PACKAGE'])
p.link[k]=o;p.link.insert(1,'-Wl,--strip-debug');p.finish()
(p.out/'replay').replace(p.out/('replay-'+mode))
