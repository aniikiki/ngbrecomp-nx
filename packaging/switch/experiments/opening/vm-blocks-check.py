"""Exercise the real flag builder and address guard after mapped pages change."""
import runpy,tempfile,subprocess
from pathlib import Path
p=Path(__file__).parent
m=runpy.run_path(str(p/'vm-blocks.py'))
d=Path('build/switch-runtime/core-perf/opening-full-page')
v=m['vm']((d/'vm.c').read_text())
a=v.index('uint32_t opening_end4');b=v.index('#include',a)
h=m['header']((d/'template.h').read_text());i=h.index('        extern uint32_t opening_full_groups;');j=h.index('        if (__builtin_expect(address < reg_ends',i)
c='#include <stdint.h>\n#include <assert.h>\n#include <stdio.h>\n'+v[a:b]+'''
static uintptr_t fast(uint32_t address,unsigned bytes){
 uintptr_t ngb_fast_ram=1;
'''+h[i:j]+'''
 return 0;
}
int main(){
 enum{B=0x1000000}; uint32_t rng=1234;unsigned hit=0,tests=0;
 for(unsigned step=0;step<600;step++){
  rng=rng*1664525+1013904223;
  unsigned start=(step==0?0:(rng>>16)%530),n=(step==0?512:1+(rng&31));
  for(unsigned p=start;p<start+n;p++)
   opening_end4[4096+p]=(step%4!=1)?((4096+p)*4096+4093):0;
  refresh_groups(start,n);
  for(unsigned g=0;g<32;g++){
   int full=1;for(unsigned k=0;k<16;k++)full &= opening_end4[4096+16*g+k]!=0;
   for(unsigned w=1;w<=4;w++)for(unsigned k=0;k<16;k++)for(unsigned o=4092;o<4096;o++){
    uint32_t off=k*4096+o,addr=B+(g<<16)+off;
    uintptr_t got=fast(addr,w);assert(!!got==(full && off+w<=65536));
    if(got){assert(got==1u+addr);for(unsigned z=0;z<w;z++)assert(opening_end4[(addr+z)>>12]);hit++;}
    tests++;
   }
  }
  assert(!fast(B-1,1)&&!fast(B+0x200000,1)&&!fast(0xffffffff,4));
 }
 printf("%u cases, %u eligible\\n",tests,hit);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'t.c';f.write_text(c)
 subprocess.run(['cc','-O2',f,'-o',f.with_suffix('')],check=True)
 subprocess.run([f.with_suffix('')],check=True)
