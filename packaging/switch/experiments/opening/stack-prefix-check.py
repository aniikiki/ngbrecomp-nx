"""Run real VM allocate, decommit, pin and release against the measured prefix."""
import tempfile,subprocess,runpy
from pathlib import Path
p=Path(__file__).parent
api=runpy.run_path(str(p/'stack-prefix.py'));lo,hi=api['bounds']()
s=api['vm'](Path('build/switch-runtime/core-perf/opening-full-page/vm.c').read_text())
s+=r'''
#include <assert.h>
#include <stdlib.h>
int main(void){
 unsigned char *ram=calloc(1,NGB_RAM_BYTES);assert(ram);ngb_vm_init(ram);
 uint32_t a=LO,n=HI-LO;
 assert(!sw_limit_words && !ngb_vm_allocate(&a,&n,0,0x3000,4));
 assert(sw_limit_words==(HI-LO)/4);
 for(uint32_t hole=LO;hole<HI;hole+=4096){
  a=hole;n=4096;assert(!ngb_vm_free(&a,&n,0x4000));
  assert(sw_limit_words==(hole-LO)/4&&!ngb_vm_access(hole,4));
  assert(!ngb_vm_allocate(&a,&n,0,0x1000,4));
  assert(sw_limit_words==(HI-LO)/4);
 }
 assert(ngb_vm_pin(LO,4096,0));a=LO;n=0;assert(ngb_vm_free(&a,&n,0x8000));
 assert(sw_limit_words==(HI-LO)/4);assert(ngb_vm_pin(LO,4096,1));
 assert(!ngb_vm_free(&a,&n,0x8000) && !sw_limit_words);ngb_vm_init(NULL);
 assert(!sw_limit_words);free(ram);
}
'''.replace('LO',str(lo)+'u').replace('HI',str(hi)+'u')
with tempfile.TemporaryDirectory() as td:
 d=Path(td);(d/'check.c').write_text(s)
 subprocess.run(['cc','-std=c11','-O2','-Ipackaging/switch/runtime',str(d/'check.c'),'-o',str(d/'check')],check=True)
 subprocess.run([d/'check'],check=True)
print('actual VM: every page decommitted/recommitted, pinned release refused, final release and reset correct')
