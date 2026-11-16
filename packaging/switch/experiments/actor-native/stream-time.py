"""Isolate incremental publication cost: identical captured ARM input, on the
same thread, rotate three implementations. Exclude decompression, page/reset
copy and verification, include all instruction capture / journal generation."""
from pathlib import Path
import subprocess as sp
here=Path(__file__).resolve().parent;p=Path('/work/build/switch-runtime');d=p/'opt050/actor-stream'
s=(d/'check.c').read_text();i=s.index(' if(events[0]!=');s=s[:i]+r'''
 uint8_t out[1024];for(unsigned r=0;r<30;r++)for(unsigned sub=0;sub<3;sub++){
 unsigned mode=(sub+r)%3;
 memcpy(out,j.regs,j.meta[3]);memcpy(j.ram,j.init,RAM);unsigned ne=0,len=0;uint64_t poll=j.ticks,ent=0;
 struct timespec t0,t1;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t0);
 unsigned error=mode==0?ngb_actor_native(out,j.ram,j.pages,&poll,&ent):
 (mode==1?raw_worker:stream_worker)(out,j.ram,j.pages,&poll,&ent,tr[0],520,&ne,log[0][0],&len);
 clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t1);
 if(error||memcmp(out,j.expect,j.meta[3])||poll!=ticks[0]||ent!=entries[0])return 11;
 if(r>=3)printf("[WORKER_COST] actor=%u mode=%u ns=%llu\n",j.meta[2],mode,(unsigned long long)((t1.tv_sec-t0.tv_sec)*1000000000ll+t1.tv_nsec-t0.tv_nsec));
 }return 0;}
'''
(d/'time.c').write_text(s);sp.run(['cc','-O2','-I'+str(here),d/'time.c',d/'raw_worker.o',d/'stream_worker.o',d.parent/'actor-native/actor.o',p/'core-perf/thread-pointer.o','-pthread','-l:libz.so.1','-lm','-o',d/'time'],check=True)
