#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
unsigned span_arm=1;
extern int check_alt(void*,void*,void*),check_base(void*,void*,void*);
static unsigned char ram[8192], before[8192], expected[8192];
static uint16_t pages[2]={4096,4096};
static uint32_t rng=123;
static uint32_t next(void){rng=rng*1664525u+1013904223u;return rng;}
int main(void){
 for(unsigned off=0;off<4096;off++){
  uint32_t a[16]={0},b[16];for(unsigned i=0;i<8;i++)a[i]=next();
  a[4]=off+16; memcpy(b,a,sizeof a);
  for(unsigned i=0;i<sizeof ram;i++)before[i]=next()>>24;
  memcpy(ram,before,sizeof ram);int base_ok=check_base(a,ram,pages);if(off<=4068 && !base_ok)abort();
  memcpy(expected,ram,sizeof ram);memcpy(ram,before,sizeof ram);
  int ok=check_alt(b,ram,pages);if(ok!=(off<=4068))abort();
  if(ok && (memcmp(a,b,sizeof a)||memcmp(expected,ram,sizeof ram)))abort();
  if(!ok && memcmp(ram,before,sizeof ram))abort();
  pages[0]=0;b[4]=off+16;if(check_alt(b,ram,pages))abort();pages[0]=4096;
 }
 puts("verified 4069 eligible offsets; 27 crossing fallbacks; 4096 protected fallbacks");
}
