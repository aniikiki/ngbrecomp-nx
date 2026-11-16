"""Reuse the mapped pointer for an x86 memory ALU op and its flag read; preserve volatile access order."""
from pathlib import Path
import re,runpy,sys
p=Path(__file__).parent
reg=r'e(?:ax|cx|dx|bx|bp|sp|si|di)'
pat=re.compile(r'^    (?P<mem>MEM(?P<bits>8|16|32)\((?P<va>'+reg+r'(?: [+-] (?:0x[\da-fA-F]+|\d+))?)\)) = (?P=mem) (?P<op>[+&|^-]) (?P<rhs>'+reg+r'|0x[\dA-Fa-f]+u?|\d+);\n    _fa = \(uint32_t\)\((?P=mem)\) & (?P<mask>0x[\da-fA-F]+u); _fas = \(int32_t\)\((?P<sign>int(?:8|16|32)_t)\)\(_fa\); /\* [^\n]*? \*/',re.M)
def fast(m):
 mem,bits,va=m['mem'],m['bits'],m['va']
 assert int(m['mask'][:-1],16)==(1<<int(bits))-1 and m['sign']=='int'+bits+'_t'
 return ('    {uint32_t ra='+va+'; if(__builtin_expect(ra<reg_ends[ra>>12],1)){volatile uint'+bits+'_t *rp=(volatile uint'+bits+'_t *)(ngb_fast_ram+(ra&0x7fffffffu));\n'+
         m[0].replace(mem,'(*rp)')+'\n    }else{\n'+m[0]+'\n    }}')
units=[2,16,1,9,29]
def transform(s,u):
 t,n=pat.subn(fast,s);assert n;print(u,n,'RMW/flags sites',flush=True);return t
if __name__=='__main__' and '--check' in sys.argv:
 import subprocess,tempfile
 seq={}
 for u in units:
  src=Path(f'build/switch-runtime/gen/recomp_{u:04}.c').read_text()
  for m in pat.finditer(src):seq[m[0]]=fast(m)
 prefix=r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
typedef struct __attribute__((packed)){uint32_t v;} U32;
typedef struct __attribute__((packed)){uint16_t v;} U16;
static uint8_t ram[8192],slow[8];static uint32_t reg_ends[1<<20],r[8],trace[4],n,_fa; static int32_t _fas;
#define ngb_fast_ram ram
static void *addr(uint32_t va,unsigned width){if(va<reg_ends[va>>12])return ram+(va&0x7fffffff);if(n>=4)abort();trace[n++]=va^width;return slow;}
#define MEM8(va) (*(volatile uint8_t*)addr((va),1))
#define MEM16(va) (((volatile U16*)addr((va),2))->v)
#define MEM32(va) (((volatile U32*)addr((va),4))->v)
'''
 for i,r in enumerate(['eax','ecx','edx','ebx','esp','ebp','esi','edi']):prefix+=f'#define {r} r[{i}]\n'
 for name,i in [('ref',0),('alt',1)]:
  prefix+='static void '+name+'(int j){switch(j){\n'
  for j,pair in enumerate(seq.items()):
   text=pair[i].replace('volatile uint32_t *rp=(volatile uint32_t *)','volatile U32 *rp=(volatile U32 *)').replace('volatile uint16_t *rp=(volatile uint16_t *)','volatile U16 *rp=(volatile U16 *)')
   if 'volatile U' in text:text=text.replace('(*rp)','rp->v')
   prefix+=f'case {j}:{{'+text+'}break;\n'
  prefix+='default:abort();}}\n'
 prefix+='static uint32_t bias[]={'+','.join(re.fullmatch(reg+r'(?: ([+-]) (0x[\da-fA-F]+|\d+))?',pat.fullmatch(k)['va']).expand(r'\1\2') or '0' for k in seq)+'};\n'
 prefix+=r'''
int main(void){uint8_t expected[8192],es[8];uint32_t et[4],ec,ef;int32_t efs;
 for(unsigned j=0;j<sizeof bias/sizeof *bias;j++) for(unsigned pg=0;pg<2;pg++)for(unsigned hi=0;hi<2;hi++)for(unsigned off=4088;off<4104;off++){
 uint32_t va=(hi<<31)+off;reg_ends[va>>12]=pg?(va&~4095u)+4093u:0;
 for(unsigned arm=0;arm<2;arm++){
 for(unsigned a=0;a<8;a++)r[a]=va-bias[j];memset(ram,0xbd,sizeof ram);memset(slow,0x73,sizeof slow);memset(trace,0,sizeof trace);n=0;
 if(arm)alt(j);else ref(j);
 if(!arm){memcpy(expected,ram,sizeof ram);memcpy(es,slow,8);memcpy(et,trace,sizeof et);ec=n;ef=_fa;efs=_fas;}
 else if(memcmp(expected,ram,sizeof ram)||memcmp(es,slow,8)||memcmp(et,trace,sizeof et)||ec!=n||ef!=_fa||efs!=_fas)abort();
 }}printf("%zu distinct blocks matched at both aliases, page boundaries and unmapped words\n",sizeof bias/sizeof *bias);}
'''
 with tempfile.TemporaryDirectory() as td:
  f=Path(td)/'check.c';f.write_text(prefix);o=f.with_suffix('')
  subprocess.run(['cc','-O0','-fno-strict-aliasing',f,'-o',o],check=True);subprocess.run([o],check=True)
elif __name__=='__main__':runpy.run_path(str(p/'model-copy.py'))['build']('rmw-flags',[(True,[2,16]),(False,[1,9,29])],transform)
