#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#define RECOMP_GENERATED_CODE
#include "particle_prepare.h"

RECOMP_TLS RecompRegs g_regs;
uint64_t ngb_guest_polls, ngb_reg_entries;
unsigned ngb_pending_dpcs, ngb_poll_mask;
uint32_t ngb_reg_recent[32], ngb_reg_current_va;
unsigned char *ngb_fast_ram, **ngb_guest_banks[64];
uint16_t ngb_fast_page_bytes[1u << 20];
uintptr_t ngb_guest_scalar_fallback(uint32_t a, size_t n) { assert(a <= NGB_RAM_BYTES - n); return (uintptr_t)(ngb_fast_ram + a); }
void *ngb_guest_high_vector(uint32_t a) { (void)a; abort(); }
void ngb_vector_read_slow(uint32_t a, uint32_t v[4]) { memcpy(v,ngb_fast_ram+a,16); }
void ngb_vector_write_slow(uint32_t a, const uint32_t v[4]) { memcpy(ngb_fast_ram+a,v,16); }
void ngb_poll_due(uint64_t ticket) { (void)ticket; abort(); }
static void checkpoint(uint32_t va) {
    ngb_reg_recent[ngb_reg_entries++ & 31] = ngb_reg_current_va = va;
    ngb_guest_block_poll();
}
#undef RECOMP_ENTRY
#undef RECOMP_ABI_CALL
#define RECOMP_ENTRY(va) checkpoint(va)
#define RECOMP_ABI_CALL(va, fn) fn()
static void sub_002FE0E0(void) { abort(); }
static void sub_002EB2F0(void) { abort(); }
static void sub_000FEFE0(void) { abort(); }
#include "reference.inc"

enum { node=0x610000, world=0x950180, camera=0x977ce0, matrix_slot=0x950440, stack=0x1101000 };
struct Output {
    RecompRegs regs;
    uint64_t polls, entries;
    uint32_t current, recent[32];
    unsigned char matrix[64], saved[64], record[0x240], frame[0xa0];
};
static void snapshot(struct Output *out) {
    out->regs=g_regs; out->polls=ngb_guest_polls; out->entries=ngb_reg_entries; out->current=ngb_reg_current_va;
    memcpy(out->recent,ngb_reg_recent,sizeof out->recent);
    memcpy(out->matrix,ngb_fast_ram+world,64); memcpy(out->saved,ngb_fast_ram+matrix_slot,64);
    memcpy(out->record,ngb_fast_ram+node,sizeof out->record); memcpy(out->frame,ngb_fast_ram+stack-48,sizeof out->frame);
}
static void seed(unsigned trial) {
    static const uint32_t values[]={0,0x80000000,1,0x807fffff,0xc0000000,0x3f7ffffe,0x7f7fffff,0x3e555555,0x7f800000,0x7fc12345,0xffc05432};
    memset(&g_regs,0x65,sizeof g_regs);
    uint32_t state=trial+1; const uint32_t area[]={node,world-64,camera};
    for(unsigned i=0;i<3;i++) for(unsigned j=0;j<(i==0?0x240:i==1?128:64);j+=4) {
        state=state*1664525u+1013904223u;
        MEM32(area[i]+j)=values[(state>>16) % (trial & 1 ? 6 : sizeof values/sizeof *values)];
    }
    memset(ngb_fast_ram+matrix_slot,0x5c,64); memset(ngb_fast_ram+stack-48,0x93,0xa0);
    MEM32(0xd52688)=matrix_slot+64;
    esi=ebx=edi=node; edx=1; esp=stack;
    ngb_poll_mask=63; ngb_guest_polls=trial%60; ngb_reg_entries=80+trial;
    memset(ngb_reg_recent,0x35,sizeof ngb_reg_recent); ngb_reg_current_va=0x55555555;
}
int main(void) {
    ngb_fast_ram=calloc(1,NGB_RAM_BYTES); assert(ngb_fast_ram);
    for(unsigned i=0;i<NGB_RAM_BYTES/4096;i++) ngb_fast_page_bytes[i]=4096;
    for(unsigned trial=0;trial<128;trial++) for(unsigned which=0;which<4;which++) {
        const uint32_t bp=stack+0x80; struct Output ref={0}, got={0};
        seed(trial);
        switch(which) {
        case 0: ref_move(bp); break;
        case 1: ref_model_a(bp); break;
        case 2: ref_model_b(bp); break;
        default: ref_view(bp); break;
        }
        snapshot(&ref); seed(trial);
        struct Output before={0}; snapshot(&before);
        int ok=which==0?particle_move():which==3?particle_view_position(bp):
            particle_model_matrix(bp,which==1?0x00124aef:0x00124dbf);
        snapshot(&got);
        if(!ok) {
            assert(!(trial & 1) && !memcmp(&before,&got,sizeof before));
            continue;
        }
        if(memcmp(&ref,&got,sizeof ref)) {
            fprintf(stderr,"particle mismatch on kernel %u, trial %u, accepted %d\n",which,trial,ok);
            for(size_t i=0;i<sizeof ref;i++) {
                unsigned char a=((unsigned char*)&ref)[i], b=((unsigned char*)&got)[i];
                if(a!=b) fprintf(stderr,"offset %zu: %02x != %02x\n",i,a,b);
            }
            return 1;
        }
    }
    for(unsigned trial=0;trial<256;trial++) {
        uint32_t index=trial%32, owner=0x4b4e50+index*0x2800;
        if ((trial & 0x12) == 2) continue;
        struct Output ref={0}, got={0};
        for(unsigned native=0;native<2;native++) {
            seed(trial); eax=owner; ngb_guest_polls=5;
            MEM8(owner+0x27a0)=0xff; MEM8(0x8b3eb8+index)=trial;
            if (native) { assert(particle_unlinked_owner()); snapshot(&got); }
            else { sub_001BDD10(); snapshot(&ref); }
        }
        assert(!memcmp(&ref,&got,sizeof ref));
        eax=owner; MEM8(owner+0x27a0)=index; assert(!particle_unlinked_owner());
        MEM8(owner+0x27a0)=0xff; MEM8(0x8b3eb8+index)=2; assert(!particle_unlinked_owner());
    }
    const uint32_t desc=node+0x1000, array=stack+0xff0;
    for(unsigned count=1;count<=16;count++) {
        seed(count); edi=node; ebx=desc; MEM32(desc)=array; MEM8(node+0x230)=0x62; MEM16(node+0x21e)=count;
        memset(ngb_fast_ram+array-1,0xfa,16*count+2);
        ngb_guest_polls=0; assert(particle_flat_vertices());
        assert(eax==16*count && edx==count && ecx==count && esi==MEM32(node+0x20c) && ngb_guest_polls==count*2);
        for(unsigned i=0;i<count;i++) {
            assert(!memcmp(ngb_fast_ram+array+16*i,ngb_fast_ram+node+16*i,12));
            assert(MEM32(array+16*i+12)==esi);
        }
        assert(MEM8(array-1)==0xfa && MEM8(array+16*count)==0xfa);
    }
    ngb_guest_polls=63; assert(!particle_flat_vertices() && !particle_view_position(stack));
    ngb_guest_polls=0; MEM32(desc)=node; assert(!particle_flat_vertices());
    MEM32(desc)=array; ngb_fast_page_bytes[(array+255)>>12]=0; assert(!particle_flat_vertices());
    MEM32(0xd52688)=world+64; assert(!particle_view_position(stack));
    esp=0xfffffff0u; assert(!particle_flat_vertices() && !particle_model_matrix(0,0x00124aef));
    ngb_poll_mask=18; assert(!particle_quiet_polls(1));
    const unsigned masks[]={0,1,3,63,0xffffffff};
    for(unsigned i=0;i<sizeof masks/sizeof *masks;i++) for(unsigned t=0;t<128;t++) {
        ngb_poll_mask=masks[i]; ngb_guest_polls=UINT64_MAX-t;
        int quiet=1;
        for(unsigned n=1;n<=32;n++) {
            if (!((ngb_guest_polls+n) & ngb_poll_mask)) quiet=0;
            assert(particle_quiet_polls(n)==quiet);
        }
    }
    seed(1); ngb_pending_dpcs=1;
    assert(!particle_three_calls_ready() && !particle_flat_vertices() && !particle_view_position(stack));
    puts("PASS particle arithmetic, matrix stack, scheduling, vertex bounds and overlap");
    free(ngb_fast_ram);
}
