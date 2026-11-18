"""Differential test of the native DrawVertices leaf against the generated XDK body."""
from pathlib import Path
import subprocess, tempfile
exp=Path(__file__).resolve().parent
root=exp.parents[3]
src=(root/'build/switch-runtime/gen/recomp_0044.c').read_text()
i=src.index('void d3d_orig_003C9A70(void)')
src=src[src.index('{',i):src.index('\n}',i)+2]
h=r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
using U=uint32_t;
alignas(16) static unsigned char mem[4<<20],before[sizeof(mem)],after[sizeof(mem)];
enum { EAX,ECX,EDX,EBX,ESP,EBP,ESI,EDI, kDevicePtr=0x3d83c8, D3DF_CDevice_SetStateVB=0};
static bool g_take[]={true};
static U eax,ecx,edx,ebx,esp,g_ebp,g_seh_ebp,esi,edi;
#define MEM32(a) (*(U*)(mem+(a)))
#define CMP_B(a,b) ((a)<(b))
#define CMP_BE(a,b) ((a)<=(b))
#define CMP_AE(a,b) ((a)>=(b))
#define PUSH32(s,v) do{(s)-=4;MEM32(s)=(v);}while(0)
#define POP32(s,v) do{(v)=MEM32(s);(s)+=4;}while(0)
#define RECOMP_ENTRY(x)
#define RECOMP_ABI_CALL(a,f) f()
#define ngb_guest_block_poll()
static void sub_003D1EF0(){assert(g_take[0]);eax=0;esp+=12;}
static void sub_003CAB80(){assert(false);}
static U R32(U a){return MEM32(a);}
static void* DirectPage(U a,U n){return a+n>sizeof(mem)||(a>>12)!=((a+n-1)>>12)?nullptr:mem+a;}
static void original()
'''
m=r'''
int main(){
 constexpr U D=0x50000,P=0x60000,S=0x10100;
 U tests=0;
 for (U n:{1u,2u,255u,256u,257u,512u,513u,1023u,2049u,65536u})
 for(U start:{0u,0x1040u,0x00fffffeu}) for(U prim:{1u,4u,5u,6u,9u}){
   memset(mem,0x65,sizeof mem);MEM32(kDevicePtr)=D;MEM32(D)=P;MEM32(D+4)=P+4000;MEM32(S+4)=prim;
   U input[]={n,start,0x906u,0x800u,S,0x345u,0x891u,0x456u},regs[8];
   eax=n;ecx=start;edx=input[2];ebx=input[3];esp=S;g_ebp=g_seh_ebp=input[5];esi=input[6];edi=input[7];
   memcpy(before,mem,sizeof mem);original();memcpy(after,mem,sizeof mem);
   U expect[]={eax,ecx,edx,ebx,esp,g_ebp,esi,edi};memcpy(mem,before,sizeof mem);memcpy(regs,input,sizeof regs);
   assert(native_linear(regs));assert(!memcmp(regs,expect,sizeof regs));assert(!memcmp(mem,after,sizeof mem));++tests;
 }
 printf("%u DrawVertices inputs: identical guest memory (including the FIFO) and registers\n",tests);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp);(t/'verify.cpp').write_text(h+src+'\n'+(exp/'native-linear.inc').read_text()+m)
 subprocess.run(['c++','-O2','-std=c++17','-fno-strict-aliasing',str(t/'verify.cpp'),'-o',str(t/'verify')],check=True)
 subprocess.run([str(t/'verify')],check=True)
