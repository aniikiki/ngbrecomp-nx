"""Check bits and floating-point exceptions against actual generated reference."""
from pathlib import Path
import tempfile,subprocess
h=Path('build/switch-runtime/gen/recomp_types.h').read_text()
s='#include <stdint.h>\n#include <math.h>\n#include <fenv.h>\n#include <string.h>\n#include <stdio.h>\n#pragma STDC FENV_ACCESS ON\n'
s+=h[h.index('static inline double recomp_fp_round24'):h.index('#define RECOMP_FP_PC')]
s+=Path(__file__).with_name('round-range.inc').read_text()
s+=r'''
__attribute__((noinline)) static double a(double x){return recomp_fp_round24(x);}
__attribute__((noinline)) static double b(double x){return ngb_round_range(x);}
int main(void){int modes[]={FE_TONEAREST,FE_DOWNWARD,FE_UPWARD,FE_TOWARDZERO};unsigned n=0;
for(unsigned m=0;m<4;m++){if(fesetround(modes[m]))return 2;
for(unsigned e=0;e<2048;e++)for(unsigned sign=0;sign<2;sign++)for(unsigned i=0;i<12;i++){
 uint64_t fractions[]={0,1,0xfffffffffffffull,0xfffffe0000000ull,0xfffffe0000001ull,0xfffffdfffffffull,1ull<<28,(1ull<<28)-1,(1ull<<28)+1,3ull<<28,0x8000000000000ull,0x5777777777777ull};
 uint64_t bits=((uint64_t)sign<<63)|((uint64_t)e<<52)|fractions[i];double x;memcpy(&x,&bits,8);
 feclearexcept(FE_ALL_EXCEPT);volatile double u=a(x);int fu=fetestexcept(FE_ALL_EXCEPT);
 feclearexcept(FE_ALL_EXCEPT);volatile double v=b(x);int fv=fetestexcept(FE_ALL_EXCEPT);
 if(memcmp((const void*)&u,(const void*)&v,8)||fu!=fv){fprintf(stderr,"mismatch %llx %u %d %d\n",(unsigned long long)bits,m,fu,fv);return 1;}n++;}}
 printf("%u results and exception flags match\n",n);}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'test.c';f.write_text(s);exe=f.with_suffix('')
 subprocess.run(['cc','-O2','-frounding-math',str(f),'-lm','-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
