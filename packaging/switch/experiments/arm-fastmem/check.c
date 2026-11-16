// Exercise the actual fault/resume instruction and verify physical aliasing.
// The fallback records the requested VA, substituting a diagnostic word.
#include <assert.h>
#include <stdio.h>
#include "access.h"
uint16_t ngb_fast_page_bytes[1u<<20];
unsigned char *ngb_fast_ram;
static uint32_t special, last, calls;
uintptr_t ngb_guest_scalar_fallback(uint32_t va,size_t n) {
    assert(n==4);last=va;calls++;return (uintptr_t)&special;
}
void *ngb_alias_create(void);
void ngb_alias_destroy(void *);
void ngb_alias_sync(unsigned,unsigned);
int main(void) {
    uint32_t va=0x2000000,alias=va|0x80000000u;
    ngb_fast_ram=ngb_alias_create();
    ngb_fast_page_bytes[va>>12]=ngb_fast_page_bytes[alias>>12]=4096;
    ngb_alias_sync(va>>12,1);ngb_alias_sync(alias>>12,1);
    ngb_shadow_store32(va,0x98abc012);
    assert(ngb_shadow_load32(alias)==0x98abc012 && !calls);
    ngb_fast_page_bytes[va>>12]=0;ngb_alias_sync(va>>12,1);
    ngb_shadow_store32(va,12345);assert(calls==1 && last==va && special==12345);
    assert(ngb_shadow_load32(va)==12345 && calls==2);
    assert(ngb_shadow_load32(alias)==0x98abc012 && calls==2);
    assert(ngb_shadow_load32(0xfd700000)==12345 && calls==3 && last==0xfd700000);
    assert(ngb_shadow_load32(alias+4094)==12345 && calls==4 && last==alias+4094);
    ngb_fast_page_bytes[va>>12]=4096;ngb_alias_sync(va>>12,1);
    assert(ngb_shadow_load32(va)==0x98abc012 && calls==4);
    ngb_alias_destroy(ngb_fast_ram);puts("ARM mapped, fault, MMIO, boundary and remap checks passed");
}
