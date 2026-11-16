"""Compile the generated comparisons and actual transformed text; compare every exit."""
from pathlib import Path
import re,runpy,tempfile,subprocess
p=Path(__file__).resolve().parent
s=Path('build/switch-runtime/gen/recomp_0028.c').read_text()
v=runpy.run_path(str(p/'material-compare-chain.py'))['transform'](s,28)
def body(source):
 t=source.split('loc_0030B8BC: ;',1)[1].split('loc_0030B967: ;',1)[0]
 for i,(c,e) in enumerate(zip(['B8C7','B8DD','B8F3','B916','B939','B94F'],['B8D2','B8E8','B90B','B92E','B944','B967'])):
  end='loc_0030'+e+': ;'
  t=re.sub(r'loc_0030'+c+r': ;.*?(?='+end+r'|\Z)',f'loc_0030{c}: ; return (Result){{{i},eax,edi,_fa,_fb,_fas,_fbs}};\n',t,flags=re.S)
 return t+'loc_0030B967: ; return (Result){6,eax,edi,_fa,_fb,_fas,_fbs};}'
pre='''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
typedef struct {uint32_t end,eax,edi,fa,fb; int32_t fas,fbs;} Result;
static uint32_t reg_ends[1<<20],ram[0x980000/4],other[32]; static unsigned char *ngb_fast_ram=(unsigned char*)ram;
static uint32_t refword(uint32_t a){if(a>=0x977000 && a<0x978000)return ram[a/4];
 if(a<reg_ends[a>>12]){uint32_t v;memcpy(&v,ngb_fast_ram+(a&0x7fffffff),4);return v;}return other[(a>>2)&31];}
#define MEM32(a) refword(a)
#define CMP_EQ(a,b) ((a)==(b))
'''
fn='(uint32_t esi){uint32_t eax=91,edi=42,_fa=0,_fb=0;int32_t _fas=0,_fbs=0;'
main='''
int main(void){unsigned cases=0;
 uint32_t shadow[]={0x97791c,0x9778f4,0x9777c8,0x9777cc,0x977910,0x9777ec};
 for(unsigned alias=0;alias<2;++alias)for(unsigned off=4056;off<4100;++off)for(unsigned avail=0;avail<3;++avail){
 uint32_t a=0x1000+off+(alias<<31);reg_ends[a>>12]=avail==0?0:avail==1?a+9:((a|4095)-2);
 for(unsigned j=0;j<64;j++)((unsigned char*)ram)[(a&0x7fffffff)+j]=j*7;
 for(unsigned j=0;j<32;j++)other[j]=j*43;
 for(unsigned mask=0;mask<64;mask++){for(unsigned j=0;j<6;j++)ram[shadow[j]/4]=refword(a+j*4)^((mask>>j)&1);
 Result x=orig(a-0x30),y=alt(a-0x30);assert(!memcmp(&x,&y,sizeof x));cases++;}
 reg_ends[a>>12]=0;}
 printf("%u comparison exits verified\\n",cases);}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'check.c';f.write_text(pre+'Result orig'+fn+body(s)+'\nResult alt'+fn+body(v)+main)
 exe=f.with_suffix('');subprocess.run(['cc','-std=c11','-O2',str(f),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
