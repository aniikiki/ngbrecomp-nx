"""Compile original and transformed blocks; compare memory and live guest registers."""
from pathlib import Path
import tempfile,subprocess
p=Path(__file__).parent
src=(p/'stage-tail.py').read_text().split("src=(p/'vector-span.py')")[0]
ns={'__file__':str(p/'stage-tail.py')};exec(src,ns)
s=Path('build/switch-runtime/gen/recomp_0028.c').read_text()
a=s.index('loc_0030BB81: ;');b=s.index('loc_0030BC30: ;',a)
orig=s[a:b];candidate=ns['transform'](s)[0];candidate=candidate[candidate.index('loc_0030BB81: ;'):candidate.index('loc_0030BC30: ;')]
head=r'''
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
static unsigned char ngb_fast_ram[0x1100000];static uint16_t ngb_fast_page_bytes[1<<20];
static uint32_t eax,ebx,ecx,edx,esi,edi,esp,ebp,_fa,_fb; static int32_t _fas,_fbs;
#define MEM32(a) (*(volatile uint32_t*)(ngb_fast_ram+((uint32_t)(a)&0x7fffffffu)))
#define PUSH32(sp,v) ((sp)-=4,MEM32(sp)=(v))
#define POP32(sp,v) ((v)=MEM32(sp),(sp)+=4)
#define CMP_EQ(a,b) ((a)==(b))
#define LO8(a) ((a)&255u)
'''
test=r'''
int main(void){unsigned n=0;for(unsigned stage=0;stage<5;stage++)for(unsigned m=0;m<16;m++)
for(unsigned x=0;x<8;x++)for(unsigned y=0;y<4;y++){
 unsigned regs[8],words[13];unsigned arg=0x1002000+y*4,stack=x&1?arg+4:0x1001004;
 if(x&4)stack=0x977988+stage*128;
 unsigned alias=(x&2)<<30;
 for(unsigned run=0;run<2;run++){eax=stage<<7;esi=stage;ebx=0xaabb;edx=0xcc;ecx=0xff;ebp=0x123456;
 edi=(arg-0x30)|alias;esp=stack;MEM32(esp-4)=5;MEM32(arg)=y;MEM32(0x3d83d0)=16;
 unsigned *q=(unsigned*)(ngb_fast_ram+0x977984+eax);unsigned *r=(unsigned*)(ngb_fast_ram+0x3d5d1c+eax);
 for(unsigned i=0;i<4;i++){q[i]=(i<2?2:i==2?1:y)^((m>>i)&1);r[i]=123;}
 ngb_fast_page_bytes[(edi+0x30)>>12]=4096;ngb_fast_page_bytes[(esp-4)>>12]=(y==3?0:4096);
 if(run)b();else a();
 unsigned rs[]={eax,ebx,ecx,edx,esi,edi,esp,ebp};unsigned ws[]={q[0],q[1],q[2],q[3],r[0],r[1],r[2],r[3],MEM32(arg),MEM32(stack-4),MEM32(0x3d83d0)};
 if(run){assert(!memcmp(regs,rs,sizeof rs)&&!memcmp(words,ws,sizeof ws));}else{memcpy(regs,rs,sizeof rs);memcpy(words,ws,sizeof ws);}}n++;}printf("%u matching block transitions\n",n);}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'check.c';f.write_text(head+'static void a(void){'+orig+'loc_0030BC30:;}\nstatic void b(void){'+candidate+'loc_0030BC30:;}\n'+test)
 subprocess.run(['cc','-O2','-fno-strict-aliasing',f,'-o',f.with_suffix('')],check=True)
 subprocess.run([f.with_suffix('')],check=True)
