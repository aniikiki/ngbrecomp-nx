#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
typedef union {uint32_t u[4];float f[4];} RecompXmm;
#include "packed-ops.h"
static uint32_t seed=17;
static uint32_t rnd(void){seed=1664525*seed+1013904223;return seed;}
int main(void){
 for(unsigned j=0;j<10000;j++){
  RecompXmm a,b;
  for(unsigned i=0;i<4;i++){a.u[i]=rnd();b.u[i]=rnd();}
  RecompXmm q=XMM_SHUFFLE(a,b,0x1b),r=XMM_ANDN(a,b),z=XMM_UNPACK_HIGH(a,b);
  for(unsigned i=0;i<4;i++){assert(q.u[i]==(i<2?a.u[3-i]:b.u[3-i]));assert(r.u[i]==(~a.u[i]&b.u[i]));assert(z.u[i]==((i&1)?b.u[2+i/2]:a.u[2+i/2]));}
  for(unsigned i=0;i<4;i++){a.f[i]=(int32_t)rnd()/8192.f;b.f[i]=((int32_t)rnd()|1)/32768.f;}
  RecompXmm m=XMM_MUL(a,b),v=XMM_DIV(a,b);
  for(unsigned i=0;i<4;i++){volatile float x=a.f[i],y=b.f[i];assert(m.f[i]==x*y && v.f[i]==x/y);}
 }
 puts("packed ops: shuffle/mask/interleave bit-exact; 40000 finite lane products/quotients agree");
}
