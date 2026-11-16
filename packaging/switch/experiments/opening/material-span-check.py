from pathlib import Path
import subprocess,tempfile,runpy
p=Path(__file__).parent
src=Path('packaging/switch/runtime/guest_memory.h').read_text().split('static inline void *ngb_ram_span',1)[1].split('\n}',1)[0]
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'check.c';f.write_text('#include <stddef.h>\n#include <stdint.h>\n#include <assert.h>\n#include <stdio.h>\nstatic unsigned char backing[4*4096],alt[4096],*ngb_fast_ram=backing,*pages[2][16384],**ngb_guest_banks[64]; static uint32_t reg_ends[1<<20];\nstatic inline void *ngb_ram_span'+src+'\n}\n'+runpy.run_path(str(p/'material-span.py'))['helper']+'''
int main(void){unsigned cases=0;for(unsigned hi=0;hi<2;hi++){unsigned base=(hi<<31)+8192;ngb_guest_banks[base>>26]=pages[hi];
for(unsigned m=0;m<3;m++){pages[hi][2]=m==2?alt:m==1?backing+8192:0;reg_ends[base>>12]=m==1?base+4093:0;
for(unsigned i=0;i<4096;i++)for(unsigned j=0;j<13;j++){size_t n=((size_t[]){0,1,4,8,12,16,20,28,56,64,76,4096,(size_t)-1})[j];assert(ms_span(base+i,n)==ngb_ram_span(base+i,n));cases++;}}}printf("%u span comparisons passed\\n",cases);}
''');subprocess.run(['cc','-O2',str(f),'-o',t+'/check'],check=True);subprocess.run([t+'/check'],check=True)
