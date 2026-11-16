#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static struct { uint32_t r[8],ram[4096];unsigned nf;uint32_t faults[64]; } st,initial,expect;
#define eax st.r[0]
#define ecx st.r[1]
#define edx st.r[2]
#define ebx st.r[3]
#define esp st.r[4]
#define ebp st.r[5]
#define esi st.r[6]
#define edi st.r[7]
#define ngb_fast_ram ((unsigned char*)st.ram)
static uint16_t ngb_fast_page_bytes[4];
static uintptr_t ptr(uint32_t a){
 if(a+4>sizeof(st.ram))abort();
 if((a&4095)+4>ngb_fast_page_bytes[a>>12])st.faults[st.nf++]=a;
 return (uintptr_t)(ngb_fast_ram+a);
}
#define MEM32(a) (*(volatile uint32_t*)ptr(a))
#define PUSH32(s,v) do{uint32_t val=(v);(s)-=4;MEM32(s)=val;}while(0)
#define POP32(s,d) do{d=MEM32(s);(s)+=4;}while(0)
static void reference(unsigned),candidate(unsigned);
static int check(unsigned n){
 for(unsigned i=0;i<4096;i++)st.ram[i]=i*127491+6835;
 for(unsigned i=0;i<8;i++)st.r[i]=0xff003512u*i+531;
 initial=st;unsigned cases=0;
 for(unsigned i=0;i<n;i++)for(int side=-32;side<=32;side++)for(int mode=0;mode<4;mode++){
   ngb_fast_page_bytes[0]=ngb_fast_page_bytes[3]=4096;
   ngb_fast_page_bytes[1]=mode==1?0:4096;ngb_fast_page_bytes[2]=mode==2?0:mode==3?32:4096;
   initial.r[4]=8192+side*4;st=initial;reference(i);expect=st;
   st=initial;candidate(i);if(memcmp(&st,&expect,sizeof(st)))abort();++cases;
 }
 printf("Distinct groups: %u; full-state and ordered fallback comparisons: %u\n",n,cases);
 return 0;
}
