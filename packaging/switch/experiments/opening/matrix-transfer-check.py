"""Compare actual selected instructions for every partial overlap, including high aliases."""
import runpy,tempfile,subprocess
from pathlib import Path
p=Path(__file__).parent;mod=runpy.run_path(str(p/'matrix-transfer.py'));s=(mod['base']/'gen/recomp_0028.c').read_text();t=mod['transform'](s)[0]
def fragment(src,new):
 a=src.index('void sub_00305950(void)\n{');z=src.index('    POP32(esp, ecx);',a)
 a=src.index('    if ((eax&4095u)' if new else '    xmm0 = XMM_MEM(eax);',a)
 return src[a:z]
out=r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
typedef struct{unsigned char v[16];} V;
static unsigned char ngb_fast_ram[0x952000],ref[64];static uint16_t ngb_fast_page_bytes[1<<20];
static V xmm0,xmm1,xmm2,xmm3;static unsigned eax,ecx=0x950180,slow,nr,order[8],expected[8];
static V XMM_MEM(unsigned v){V x;if((v&4095)+16>ngb_fast_page_bytes[v>>12])order[slow++]=v;memcpy(&x,ngb_fast_ram+(v&0x7fffffff),16);return x;}
static void XMM_STORE(unsigned v,V x){memcpy(ngb_fast_ram+v,&x,16);}
'''
out+='static void a(void){'+fragment(s,False)+'}\nstatic void b(void){'+fragment(t,True)+'}\n'
out+=r'''
int main(void){unsigned n=0;for(unsigned pos=0;pos<2;pos++)for(int off=-64;off<=64;off++)
for(unsigned hi=0;hi<2;hi++)for(unsigned mode=0;mode<3;mode++){
 eax=((pos?0x951000:ecx)+off)|(hi<<31);ngb_fast_page_bytes[eax>>12]=mode==0?4096:mode==1?0:4050;
 V saved[4];for(unsigned run=0;run<2;run++){for(unsigned i=0;i<0x1200;i++)ngb_fast_ram[0x950000+i]=i*19+i/79;
 slow=0;if(run)b();else a();V v[]={xmm0,xmm1,xmm2,xmm3};
 if(run){assert(!memcmp(saved,v,64)&&!memcmp(ref,ngb_fast_ram+ecx,64)&&slow==nr&&!memcmp(expected,order,slow*4));}
 else{memcpy(saved,v,64);memcpy(ref,ngb_fast_ram+ecx,64);nr=slow;memcpy(expected,order,slow*4);}}n++;}
 printf("%u matching transfers\n",n);}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'a.c';f.write_text(out);subprocess.run(['cc','-O2',f,'-o',f.with_suffix('')],check=True);subprocess.run([f.with_suffix('')],check=True)
