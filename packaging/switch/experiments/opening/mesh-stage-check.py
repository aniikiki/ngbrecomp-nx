from pathlib import Path
import runpy,subprocess,tempfile
d=Path(__file__).parent
s=Path('build/switch-runtime/gen/recomp_0028.c').read_text()
mk=runpy.run_path(str(d/'mesh-stage.py'))['transform']
def fun(s,name):
 a=s.index('loc_0030BFA7: ;');b=s.index('loc_0030C009:',a)
 return 'static unsigned '+name+'(unsigned ebp,unsigned esi){unsigned _fa,_fb;int _fas,_fbs;'+s[a:b]+'loc_0030C009:return 1;loc_0030C01D:return 0;}'
h='''#include <stdint.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
static unsigned eax,ecx,edi;
static unsigned char ram[0x1000000] __attribute__((aligned(16))); static unsigned char* ngb_fast_ram=ram;
#define MEM32(a) (*(volatile unsigned*)(ram+(a)))
#define CMP_EQ(a,b) ((a)==(b))
'''
tail='''
struct state {unsigned words[7],regs[3],exit;};
int main(void){unsigned n=0;
for(unsigned i=0;i<8;i++)for(unsigned mask=0;mask<16;mask++)for(unsigned base=0;base<2;base++){
unsigned off[]={0xC0EBB0,0x3D83D0,0x9779A8+(i<<7),0x9779B8+(i<<7),0x3D5D40+(i<<7),0x3D5D50+(i<<7),0x977968+i*4};
unsigned initial[]={5,mask&8?0xFFFFFFFF:0,mask&1?3:0,mask&2?3:0,7,9,mask&4?0xFFC:0};struct state v[2];
for(int arm=0;arm<2;arm++){for(int j=0;j<7;j++)MEM32(off[j])=initial[j];eax=9;ecx=7;edi=5;ngb_fast_ram=base?ram:0;
v[arm].exit=arm?candidate(i,3):original(i,3);
v[arm].regs[0]=eax;v[arm].regs[1]=ecx;v[arm].regs[2]=edi;
for(int j=0;j<7;j++)v[arm].words[j]=MEM32(off[j]);}
assert(!memcmp(v,v+1,sizeof(v[0])));n++;}printf("%u cases passed\\n",n);}
'''
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'check.c';f.write_text(h+fun(s,'original')+fun(mk(s,28),'candidate')+tail)
 subprocess.run(['cc','-O2',str(f),'-o',t+'/check'],check=True);subprocess.run([t+'/check'],check=True)
