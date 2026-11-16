// Linux/AArch64 offline experiment. Normal mapped words use one guest-VA
// indexed load/store. A protection fault resumes at this site's checked path.
#pragma once
#include "guest_memory.h"
extern unsigned char *ngb_alias;
#define NGB_FIXUP "\n.pushsection ngb_fault,\"a\",@progbits\n.balign 4\n.long 1b-.\n.long %l[slow]-.\n.popsection\n"
static inline __attribute__((always_inline)) uint32_t ngb_shadow_load32(uint32_t va)
{
    uint32_t v;
    asm goto volatile("1: ldr %w0,[%1,%w2,uxtw]" NGB_FIXUP
        : "=r"(v) : "r"(ngb_alias),"r"(va) : "memory" : slow);
    return v;
slow:
    return *(volatile uint32_t *)ngb_guest_scalar(va,4);
}
static inline __attribute__((always_inline)) void ngb_shadow_store32(uint32_t va,uint32_t v)
{
    asm goto volatile("1: str %w0,[%1,%w2,uxtw]" NGB_FIXUP
        :: "r"(v),"r"(ngb_alias),"r"(va) : "memory" : slow);
    return;
slow:
    *(volatile uint32_t *)ngb_guest_scalar(va,4) = v;
}
