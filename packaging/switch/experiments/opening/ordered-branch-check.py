"""Compile the actual generated comparison on AArch64; compare AH, intact EAX bits and JP."""
import runpy,subprocess,tempfile
from pathlib import Path
p=Path(__file__).parent
src=Path('build/switch-runtime/gen/recomp_0028.c').read_text().split('void sub_0030D630(void)\n{')[1].split('\n}')[0]
wrap=runpy.run_path(str(p/'ordered-branch.py'))['transform']
orig=next(l for l in src.splitlines() if '/* lahf (ucomiss) */' in l)
new=next(l for l in wrap(src,28).splitlines() if 'unsigned ah; __asm__' in l)
test=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#define FN(N,B) __attribute__((noinline)) unsigned N(double _fca,double _fcb,unsigned eax){ B return eax; }
FN(ref,ORIGINAL)
FN(arm,CANDIDATE)
int main(void){
 uint32_t v[]={0,0x80000000,1,0x80000001,0x7f800000,0xff800000,0x7fc00000,0xffc00001,0x7f800001,0x3f800000,0xbf800000,0x00800000,0x7f7fffff};
 unsigned n=0;for(unsigned i=0;i<13;i++)for(unsigned j=0;j<13;j++)for(unsigned k=0;k<256;k++){
 float a,b;memcpy(&a,&v[i],4);memcpy(&b,&v[j],4);unsigned input=0xa55a00c3u|(k<<8);
 unsigned l=ref(a,b,input),r=arm(a,b,input); assert(l==r);
 unsigned x=(l>>8)&0x44,y=x; y^=y>>4;y^=y>>2;y^=y>>1;
 assert(((~y)&1)==((((r>>8)&0x44)!=0x40)));n++;}
 printf("%u register and branch comparisons passed\n",n);}
'''.replace('ORIGINAL',orig.strip()).replace('CANDIDATE',new.strip())
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'check.c';f.write_text(test);subprocess.run(['cc','-O2',str(f),'-o',tmp+'/check'],check=True);subprocess.run([tmp+'/check'],check=True)
