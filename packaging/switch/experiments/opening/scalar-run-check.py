"""Differential fast/fallback test using real transformed statements, including base overwrite."""
from pathlib import Path
import runpy,subprocess,tempfile
transform=runpy.run_path(str(Path(__file__).with_name('scalar-run.py')))['transform']
s="""    MEM32(esi + 8) = ecx;
    edi = MEM32(esi + 8);
    MEM16(esi + 4) = edi;
    ebx = MEM8(esi + 5);
    edx = MEM32(esi);
    esi = MEM32(edi);
"""
t,g=transform(s);assert g==[(0,5)] and "va=esi+" in t
src=r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>
static unsigned char mem[1<<16],ref[1<<16], *ngb_fast_ram=mem;
static uint16_t ngb_fast_page_bytes[1<<20];
static uint32_t esi,ecx,edi,ebx,edx,tr[16];static unsigned nt;
static void *lookup(uint32_t a,unsigned n){
 if((a&4095)+n>ngb_fast_page_bytes[a>>12])tr[nt++]=a;
 return mem+(a&32767);}
#define MEM32(a) (*(volatile uint32_t*)lookup(a,4))
#define MEM16(a) (*(volatile uint16_t*)lookup(a,2))
#define MEM8(a) (*(volatile uint8_t*)lookup(a,1))
'''
src+='static void a(void){\n'+s+'}\nstatic void b(void){\n'+t+'}\n'
src+=r'''
int main(void){for(unsigned alias=0;alias<2;alias++)for(unsigned limit=0;limit<=4096;limit+=256)
 for(unsigned o=0;o<4096;o++){uint32_t base=4096+o+(alias<<31);ngb_fast_page_bytes[base>>12]=limit;
 uint32_t saved[16],regs[4];unsigned count=0;
 for(unsigned k=0;k<2;k++){memset(mem+4096,170,4112);esi=base;edi=ebx=0;ecx=base*131u;nt=0;
 if(!k){a();memcpy(ref+4096,mem+4096,4112);memcpy(saved,tr,nt*4);count=nt;regs[0]=esi;regs[1]=edi;regs[2]=ebx;regs[3]=edx;}
 else{b();assert(!memcmp(ref+4096,mem+4096,4112)&&nt==count&&!memcmp(saved,tr,nt*4)&&esi==regs[0]&&edi==regs[1]&&ebx==regs[2]&&edx==regs[3]);}}} }
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'check.c';f.write_text(src);exe=f.with_suffix('')
 subprocess.run(['cc','-O2','-fno-strict-aliasing',str(f),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print('139264 scalar-run differential cases passed')
# Audit every actual generated fast path against its corresponding original
# instructions, independently of the transform's parsed tuple or group list.
import re
for u in (16,28,29):
 src=Path(f'build/switch-runtime/gen/recomp_{u:04}.c').read_text()
 out,groups=transform(src)
 pat=r'    \{ uint32_t va=(\w+)\+(\d+)u;.*?\n(.*?)    \}else\{\n(.*?)    \} \}\n'
 runs=re.findall(pat,out,re.S);assert len(runs)==len(groups)
 for base,low,fast,orig in runs:
  a=fast.splitlines();b=orig.splitlines();assert len(a)==len(b)
  for direct,guest in zip(a,b):
   addr=re.search(r'MEM(\d+)\((\w+)(?: \+ (0x\w+|\d+))?\)',guest)
   assert base==addr[2] and direct.strip()==guest.strip().replace(addr[0],f'*(volatile uint{addr[1]}_t *)(p+{int(addr[3] or "0",0)-int(low)})')
 print('checked generated scalar addresses and operands',u,len(runs))
