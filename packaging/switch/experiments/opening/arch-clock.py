"""Offline control: base guest runtime time on this ARM host's actual counter, with measured frequency."""
from pathlib import Path
import math,subprocess,tempfile
def install(p,src):
 with tempfile.TemporaryDirectory() as td:
  c=Path(td)/'freq.c';exe=c.with_suffix('')
  c.write_text('#include <stdio.h>\nint main(void){unsigned long x;__asm__ volatile("mrs %0,cntfrq_el0":"=r"(x));printf("%lu",x);}')
  subprocess.run(['cc',c,'-o',exe],check=True)
  hz=int(subprocess.check_output([exe]))
 assert 1000000<=hz<=4000000000
 g=math.gcd(hz,10**9);den=hz//g;num=10**9//g
 body=f'''static inline uint64_t arch_clock_ns(void){{
  uint64_t t; __asm__ volatile("isb; mrs %0,cntvct_el0":"=r"(t)::"memory");
  return t/{den}ULL*{num}ULL+(t%{den}ULL)*{num}ULL/{den}ULL;
}}
'''
 with tempfile.TemporaryDirectory() as td:
  c=Path(td)/'check.c';exe=c.with_suffix('')
  c.write_text('#include <stdint.h>\n#include <time.h>\n#include <stdio.h>\n'+body+'''
static uint64_t ref(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC_RAW,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
int main(void){uint64_t a=ref(),t=arch_clock_ns(),prev=t;
for(int i=0;i<10000;i++){uint64_t n=arch_clock_ns();if(n<prev)return 1;prev=n;}
struct timespec wait={0,50000000};nanosleep(&wait,0);
uint64_t dt=arch_clock_ns()-t,dr=ref()-a;printf("raw and counter deltas: %lu %lu\\n",dr,dt);return !dr || dt<dr*99/100 || dt>dr*101/100;}
''')
  subprocess.run(['cc','-O2',c,'-o',exe],check=True);subprocess.run([exe],check=True)
 import sys
 if '--ohci-tick-limit' in sys.argv:
  assert hz%1000==0
  body+=f"""
/* First raw counter satisfying floor(t*num/den) >= boundary. */
static uint64_t arch_ceil_tick(uint64_t ns){{return ns/{num}ULL*{den}ULL+(ns%{num}ULL*{den}ULL+{num-1}ULL)/{num}ULL;}}
uint64_t opening_ohci_frames(uint64_t epoch){{
 static uint64_t last_start,last_epoch,lo,hi; static int valid;
 uint64_t t; __asm__ volatile("isb; mrs %0,cntvct_el0":"=r"(t)::"memory");
 if(!valid || last_epoch!=epoch || last_start!=start_ns){{
  lo=arch_ceil_tick(start_ns+epoch);hi=lo+{hz//1000}ULL;
  last_start=start_ns;last_epoch=epoch;valid=1;
 }}
 if(t>=lo && t<hi)return 0;
 uint64_t ns=t/{den}ULL*{num}ULL+(t%{den}ULL)*{num}ULL/{den}ULL;
 return (ns-start_ns-epoch)/1000000ULL;
}}
"""
 rt=(p.out/'host-runtime.inc').read_text();k='static uint64_t now_ns(void)';a=rt.index(k);b=rt.index('\n}',a)+2
 assert 'CLOCK_MONOTONIC' in rt[a:b]
 (p.out/'arch-clock-runtime.inc').write_text(rt[:a]+body+k+'{return arch_clock_ns();}'+rt[b:])
 print('host architectural frequency',hz,flush=True)
 assert src.count('"host-runtime.inc"')==1
 return src.replace('"host-runtime.inc"','"arch-clock-runtime.inc"')
