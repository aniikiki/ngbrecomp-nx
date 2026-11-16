#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
static uint16_t ngb_fast_page_bytes[1u<<20];
static unsigned char *ngb_fast_ram;
#include "../../runtime/vm.h"
#include "region-bias.inc"
static void set(unsigned p,unsigned len){ngb_fast_page_bytes[p]=len;ngb_region_changed(p);}
static unsigned rng=11;
static unsigned nextval(void){rng=1664525u*rng+1013904223u;return rng;}
int main(void){
    ngb_fast_ram=malloc(4096); assert(ngb_fast_ram);
    for(unsigned pass=0;pass<2;++pass){
        unsigned page=pass?(1u<<19):0;
        for(unsigned i=0;i<97;++i)set(page+i,4096);
        for(unsigned t=0;t<10000;++t){
            unsigned i=page+(nextval()>>12)%97;
            set(i,(nextval()>>15)&1?4096:0);
            for(unsigned z=0;z<6;++z){
                unsigned r=(page>>4)+z;
                unsigned valid=pass==0;
                for(unsigned j=r*16;j<=r*16+16;++j)valid &= ngb_fast_page_bytes[j]==4096;
                assert((ngb_region_bias[r]!=0)==valid);
                if(valid){
                    uint32_t a=(r<<16)+65535;
                    assert(ngb_region_bias[r]+a==(uintptr_t)ngb_fast_ram+(a&0x7fffffffu));
                }
            }
        }
    }
    for(unsigned i=0;i<17;++i)set((32767u<<4)+i,4096);
    assert(!ngb_region_bias[32767]);
    for(unsigned i=0;i<16;++i)set((65535u<<4)+i,4096);
    assert(!ngb_region_bias[65535]);
    free(ngb_fast_ram); puts("region mapping: 20000 map/unmap transitions, both aliases and terminal boundaries passed");
}
