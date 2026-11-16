"""Compare ARM rounding to the generated implementation, including indefinite."""
from pathlib import Path
import subprocess,tempfile
root=Path('build/switch-runtime/gen')
s=(root/'recomp_types.h').read_text()
s=s[s.index('static inline double recomp_frndint'):s.index('\n}',s.index('static inline int64_t recomp_fist'))+2]
s='#include <stdint.h>\n#include <math.h>\n#include <stdio.h>\n#include <string.h>\n'+s+'\n'+Path(__file__).with_name('fist-round.inc').read_text()+r'''
static uint64_t n;
static int check(double x){
 for(unsigned c=0;c<4;c++)for(unsigned b=16;b<=64;b*=2){
 if(recomp_fist(x,c<<10,b)!=ngb_arm_fist(x,c<<10,b)){fprintf(stderr,"mismatch %a %u %u\n",x,c,b);return 1;}++n;}
 return 0;
}
int main(void){uint64_t u=24691;
 for(int i=0;i<100000;i++){u=u*6364136223846793005ull+1;double x;memcpy(&x,&u,8);if(check(x))return 1;}
 for(int i=-1024;i<=1024;i++){double x=i+.5;if(check(x)||check(nextafter(x,-INFINITY))||check(nextafter(x,INFINITY)))return 1;}
 for(int i=0;i<=64;i++){double x=ldexp(1.,i);for(int j=0;j<2;j++,x=-x)if(check(x)||check(nextafter(x,-INFINITY))||check(nextafter(x,INFINITY)))return 1;}
 if(check(0.)||check(-0.)||check(NAN)||check(INFINITY)||check(-INFINITY))return 1;
 printf("%llu ARM comparisons passed\n",(unsigned long long)n);}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'test.c';f.write_text(s);out=f.with_suffix('')
 subprocess.run(['cc','-O2',f,'-lm','-o',out],check=True)
 subprocess.run([out],check=True)
