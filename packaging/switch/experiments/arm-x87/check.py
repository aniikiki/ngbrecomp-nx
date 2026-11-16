"""Compile and compare the exact runtime helpers, including exponent edges."""
from pathlib import Path
import subprocess as sp,sys
here=Path(__file__).resolve().parent;root=here.parents[3];d=root/'build/switch-runtime/opt050/x87';d.mkdir(exist_ok=True)
s=(root/'build/switch-runtime/gen/recomp_types.h').read_text();s=s[s.index('static inline double recomp_fp_round24'):s.index('#define RECOMP_FP_PC')].replace('round24(', 'round24_reference(')
core=(root/'build/switch-runtime/gen/recomp_types.h').read_text()
fr=core[core.index('static inline double recomp_frndint'):core.index('/* x87 integer stores')]
a=fr.index('        double lo=floor');b=fr.index('        break;',a)
native=fr[:a]+'        __asm__("frintn %d0,%d1" : "=w"(rounded) : "w"(value));\n'+fr[b:]
fr=fr.replace('recomp_frndint','reference_frndint')+native
s='#include <math.h>\n#include <stdint.h>\n#include <stdio.h>\n#include <string.h>\n'+s+(here/'round.inc').read_text()+fr+r'''
static int check(uint64_t raw){double x,a,b;memcpy(&x,&raw,8);a=recomp_fp_round24_reference(x);b=recomp_fp_round24(x);
 for(unsigned rc=0;rc<4;rc++){double v=reference_frndint(x,rc<<10),u=recomp_frndint(x,rc<<10);if(memcmp(&v,&u,8))return 1;}
 if(memcmp(&a,&b,8)){fprintf(stderr,"mismatch %016llx %a %a\n",(unsigned long long)raw,a,b);return 1;}return 0;}
int main(void){uint64_t seed=7,n=0;for(unsigned e=0;e<2048;e++)for(unsigned sign=0;sign<2;sign++)for(unsigned p=0;p<16;p++){
 uint64_t base=((uint64_t)sign<<63)|((uint64_t)e<<52)|((uint64_t)(p&7)<<29)|((p&8)?0xfffff00000000ull:0);
 for(int j=-2;j<=2;j++){if(check(base+(1ull<<28)+j)||check(base+j))return 1;n+=2;}}
 for(int i=0;i<2000000;i++){seed^=seed<<13;seed^=seed>>7;seed^=seed<<17;if(check(seed))return 1;n++;}
 printf("%llu rounded values match bit-for-bit\n",(unsigned long long)n);}
'''
(d/'check.c').write_text(s);sp.run(['cc','-O2',d/'check.c','-lm','-o',d/'check'],check=True);sp.run([d/'check'],check=True)
