"""Compare the generated fragment against its unchanged fallback, including misalignment."""
from pathlib import Path
import runpy,tempfile,subprocess
p=Path(__file__).resolve().parent
s=Path('build/switch-runtime/gen/recomp_0044.c').read_text()
t=runpy.run_path(str(p/'light-record.py'))['transform'](s)
def fragment(s,anchor):
 a=s.index(anchor,s.index('loc_003C78C1: ;'));return s[a:s.index('    if (CMP_EQ',a)]
old=fragment(s,'    edi = MEM32'); new=fragment(t,'    {\n    uint32_t light_addr')
src="""#include <stdint.h>
#include <string.h>
#include <stdlib.h>
static unsigned char ram[8200],*ngb_fast_ram=ram;static unsigned short ngb_fast_page_bytes[1<<20];
static uint32_t eax,ebx,ecx,edx,edi,_fa,_fb;static int32_t _fas,_fbs;
typedef struct __attribute__((packed,may_alias)){uint32_t v;} U;
#define MEM32(a) (((U*)(ram+((uint32_t)(a)&0x7fffffff)))->v)
"""+'static void ref(void){'+old+'}\nstatic void alt(void){'+new+'}\n'+"""
int main(void){unsigned char orig[8200],want[8200]; for(unsigned i=0;i<8200;i++)orig[i]=i*31+5;
for(unsigned alias=0;alias<2;alias++)for(unsigned mapped=0;mapped<2;mapped++)for(unsigned i=0;i<4096;i++){
uint32_t addr=(alias<<31)+i;ngb_fast_page_bytes[addr>>12]=mapped?4096:0;
uint32_t out[7];for(int v=0;v<2;v++){memcpy(ram,orig,sizeof ram);ebx=211;eax=addr-ebx-104;edx=i%3;
if(v)alt();else ref();uint32_t regs[]={eax,ecx,edi,_fa,_fb,(uint32_t)_fas,(uint32_t)_fbs};
if(!v){memcpy(want,ram,sizeof ram);memcpy(out,regs,sizeof out);}
else if(memcmp(want,ram,sizeof ram)||memcmp(out,regs,sizeof out))abort();
}}}
"""
with tempfile.TemporaryDirectory() as tmp:
 exe=Path(tmp)/'check';subprocess.run(['cc','-O2','-x','c','-o',exe,'-'],input=src,text=True,check=True);subprocess.run([exe],check=True)
print('16384 original/candidate memory and register comparisons passed')
