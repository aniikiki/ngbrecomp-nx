"""Exercise actual VM mutations and compare the published proof against the original map."""
import tempfile,subprocess,runpy
from pathlib import Path
p=Path(__file__).parent
s=runpy.run_path(str(p/'low-words.py'))['vm'](Path('build/switch-runtime/core-perf/opening-full-page/vm.c').read_text())
s+=r'''
#include <assert.h>
#include <stdlib.h>
static void verify(void){
 unsigned p=8;
 while(p<NGB_VM_END/4096 && opening_end4[p]==p*4096+4093)++p;
 assert(lp_words==(p-8)*1024);
 uint32_t probes[]={0,1,0x7ffc,0x8000,0x8001,p*4096-4,p*4096-3,p*4096,0xffffffff,0x80008000};
 for(unsigned i=0;i<sizeof probes/sizeof *probes;i++){
  uint32_t a=probes[i],d=a-0x8000u;
  int admit=((d>>2)|(d<<30))<lp_words;assert(admit==(a>=0x8000 && a<p*4096 && !(a&3)));
  if(admit)assert(a<opening_end4[a>>12]);
 }
}
int main(void){uint8_t *ram=calloc(1,NGB_RAM_BYTES);assert(ram);ngb_vm_init(ram);verify();
 uint32_t a=NGB_VM_BEGIN,n=128*4096;assert(!ngb_vm_allocate(&a,&n,0,0x2000,4));verify();
 for(unsigned j=0;j<128;j++){a=NGB_VM_BEGIN+4096*(127-j);n=4096;assert(!ngb_vm_allocate(&a,&n,0,0x1000,4));verify();}
 unsigned rng=751;
 for(unsigned j=0;j<2048;j++){rng=rng*1664525u+1013904223u;a=NGB_VM_BEGIN+4096*((rng>>17)&127);n=4096;
 if(rng>>31)assert(!ngb_vm_free(&a,&n,0x4000));else assert(!ngb_vm_allocate(&a,&n,0,0x1000,4));verify();}
 a=NGB_VM_BEGIN;n=0;assert(!ngb_vm_free(&a,&n,0x8000));verify();ngb_vm_init(NULL);verify();free(ram);}
'''
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'check.c';f.write_text(s);exe=f.with_suffix('')
 subprocess.run(['cc','-O2','-Ipackaging/switch/runtime',f,'-o',exe],check=True);subprocess.run([exe],check=True)
print('actual VM map matches incremental prefix through reserve, out-of-order commits, 2048 mutations, release and reset')
