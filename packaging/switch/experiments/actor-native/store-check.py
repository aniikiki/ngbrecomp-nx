"""A/B the same journal before/after eliminating dead read hooks: compare all
events and record masks exactly and time only the isolated native calculation."""
from pathlib import Path
import subprocess as sp
here=Path(__file__).resolve().parent;p=Path('/work/build/switch-runtime');d=p/'opt050/actor-store-only';normal=d.parent/'actor-journal'
src=(d.parent/'actor-stream/check.c').read_text()
a=src.index(' uint32_t a=0,b=0;')
src=src[:a]+r'''
 if(n[0]!=n[1]||memcmp(log[0],log[1],n[0]*12))return 10;
 for(unsigned r=0;r<36;r++){
  for(unsigned j_=0;j_<2;j_++){unsigned mode=j_^((r/2)&1);
   memcpy(j.ram,j.init,RAM);memcpy(regs[mode],j.regs,j.meta[3]);ticks[mode]=j.ticks;
   struct timespec a,b;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&a);
   unsigned err=(mode?stream_worker:raw_worker)(regs[mode],j.ram,j.pages,&ticks[mode],&entries[mode],tr[mode],520,&events[mode],log[mode][0],&n[mode]);
   clock_gettime(CLOCK_THREAD_CPUTIME_ID,&b);if(err)abort();
   if(r>=4)printf("[STORE_COST] actor=%u mode=%u ns=%llu\n",j.meta[2],mode,(unsigned long long)((b.tv_sec-a.tv_sec)*1000000000ll+b.tv_nsec-a.tv_nsec));}}
 printf("[STORE_EXACT] id=%u polls=%u writes=%u\n",j.meta[2],events[0],n[0]);}
'''
(d/'check.c').write_text(src)
for dirname,name in [(normal,'raw_worker'),(d,'stream_worker')]:
 dst=d/(name+'.o');sp.run(['objcopy','--redefine-sym','ngb_actor_native='+name,dirname/'actor.o',dst],check=True)
 private=[l.split()[-1] for l in sp.check_output(['nm','-g','--defined-only',dst],text=True).splitlines() if 'private___tsan' in l]
 sp.run(['objcopy',*['--localize-symbol='+x for x in private],dst],check=True)
sp.run(['cc','-O2','-I'+str(here),d/'check.c',d/'raw_worker.o',d/'stream_worker.o',p/'core-perf/thread-pointer.o','-pthread','-l:libz.so.1','-lm','-o',d/'check'],check=True)
