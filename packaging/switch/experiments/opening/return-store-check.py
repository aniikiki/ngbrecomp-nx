"""Use transformed call-site text and compare bytes, ESP, fallback and callee observation."""
import subprocess,tempfile,runpy
from pathlib import Path
p=Path(__file__).resolve().parent
code=r'''
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
static uint8_t ram[8192],slow[4],initial[8192],expect[8192],savedslow[4];
static uint32_t esp,reg_ends[1<<20],calls,fault_va,seen;
#define ngb_fast_ram ram
static uintptr_t ngb_guest_scalar_fallback(uint32_t va,unsigned n){if(n!=4)abort();fault_va=va;calls++;return (uintptr_t)slow;}
static void observe(void){memcpy(&seen,calls?slow:ram+(esp&0x7fffffff),4);}
#define RECOMP_ABI_CALL(a,b) observe()
#define PUSH32(sp,v) do{(sp)-=4;uint32_t a=sp;*(volatile uint32_t*)(a<reg_ends[a>>12]?(uintptr_t)(ram+(a&0x7fffffff)):ngb_guest_scalar_fallback(a,4))=v;}while(0)
'''
line='PUSH32(esp, 0x0013E0A8u); RECOMP_ABI_CALL(0, unused);'
code+='static void orig(void){'+line+'}\nstatic void alt(void){'+runpy.run_path(str(p/'return-store.py'))['transform'](line)+'}\n'
code+=r'''
int main(void){unsigned tests=0;
for(unsigned i=0;i<sizeof ram;i++)initial[i]=i*103+7;
for(unsigned hi=0;hi<2;hi++)for(unsigned off=0;off<8192;off++)for(unsigned enabled=0;enabled<2;enabled++){
 uint32_t a=(hi<<31)+off,pg=a>>12,sp=a+4;
 reg_ends[pg]=enabled?(a&~4095u)+4093u:0;
 uint32_t expectedCalls=0;
 for(unsigned mode=0;mode<2;mode++){
  memcpy(ram,initial,sizeof ram);memset(slow,0xac,4);calls=0;fault_va=~0u;seen=0;esp=sp;
  if(mode)alt();else orig();
  if(esp!=a||seen!=0x13e0a8u||(calls&&fault_va!=a))abort();
  if(!mode){memcpy(expect,ram,sizeof ram);memcpy(savedslow,slow,4);expectedCalls=calls;}
  else if(expectedCalls!=calls||memcmp(expect,ram,sizeof ram)||memcmp(savedslow,slow,4))abort();
 }tests++;
}printf("return store equivalence %u cases\n",tests);}
'''
with tempfile.TemporaryDirectory() as td:
 f=Path(td)/'check.c';f.write_text(code)
 subprocess.run(['cc','-O2',str(f),'-o',td+'/check'],check=True);subprocess.run([td+'/check'],check=True)
