#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "guest_memory.h"
#define MEM8(a) (*(volatile uint8_t*)ngb_guest_scalar((a),1))
#define MEM16(a) (*(volatile uint16_t*)ngb_guest_scalar((a),2))
#define MEM32(a) (*(volatile uint32_t*)ngb_guest_scalar((a),4))
#define MEMF(a) (*(volatile float*)ngb_guest_scalar((a),4))
#include "direct.h"
unsigned char *ngb_fast_ram;
uint16_t ngb_fast_page_bytes[1<<20];
static uint32_t special,last,calls,size;
uintptr_t ngb_guest_scalar_fallback(uint32_t va,size_t n){last=va;size=n;calls++;return (uintptr_t)&special;}
void *ngb_alias_create(void);void ngb_alias_destroy(void*);void ngb_alias_sync(unsigned,unsigned);void ngb_alias_physical(unsigned,unsigned,const unsigned char*);
int main(void){
 ngb_fast_ram=ngb_alias_create();unsigned a=0x1100000,h=a|0x80000000;unsigned char ok[32768]={0};
 ngb_fast_page_bytes[a>>12]=ngb_fast_page_bytes[h>>12]=4096;ngb_alias_sync(a>>12,1);ok[a>>12]=1;ngb_alias_physical(a>>12,(a>>12)+1,ok);
 view_putF(a,7.25f);assert(view_getF(h)==7.25f);
 view_put16(h+6,0xabcd);assert(view_get16(a+6)==0xabcd);
 view_put8(a+8,0xfe);assert(view_get8(h+8)==0xfe && calls==0);
 view_put32(a+12,0x84fed123);assert(view_get32(h+12)==0x84fed123);
 ngb_fast_page_bytes[a>>12]=0;ngb_alias_sync(a>>12,1);
 view_putF(a,2.5f);assert(size==4 && last==a && calls==1 && view_getF(h)==7.25f);
 assert(view_getF(a)==2.5f && calls==2);
 view_put8(0xfd700001,71);assert(last==0xfd700001 && size==1 && calls==3);
 (void)view_get16(a+4095);assert(last==a+4095 && size==2 && calls==4);
 ngb_alias_destroy(ngb_fast_ram);puts("scalar sizes, float, physical alias, unmap and cross-page fallback passed");
}
