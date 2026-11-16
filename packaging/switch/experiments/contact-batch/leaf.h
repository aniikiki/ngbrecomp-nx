/* This routine may retire a FULL candidate including both matrix transforms
 * only if no checkpoint/DPC is due and each memory effect is ordinary RAM.
 * Outputs (including dead stack slots) are shadow-checked in the offline run. */
static inline int contact_leaf(unsigned fp){
    unsigned sp=esp,csr=ebx;
    if(sp<0x1001000 || sp>0x3dfe000 || (sp&3) || csr<0x7a79c6 || csr>0x7a9000 ||
        ngb_pending_dpcs || ngb_reg_entries<48 || ngb_poll_mask-(ngb_guest_polls&ngb_poll_mask)<6)return 0;
    unsigned childfp=sp-40,cs=(childfp&~15u)-64,low=((cs-8)&~15u)-32;
    unsigned char *stack=ngb_ram_span(low,sp+112-low);
    if(!stack || MEM32(sp+28)!=sp+48)return 0;
    unsigned actor=0x4b4e50+MEM8(csr)*0x2800u,n=MEM16(csr-2),box=MEM32(csr-6);
    if(actor>=0x7a0000 || n>=31 || box>0xffffffd0u || esi>0xffffffbfu)return 0;
    unsigned char *q=ngb_ram_span(esi,40);if(!q)return 0;
    unsigned ball;memcpy(&ball,q,4);
    const void *sph=ngb_ram_span(ball,16),*bx=ngb_ram_span(box+16,28);
    if(!sph||!bx)return 0;
    // Reject any physical alias to the memory we modify, including inputs
    // at a different guest VA backed by the same physical RAM.
    const void *inputs[]={sph,bx,q,ngb_fast_ram+actor,ngb_fast_ram+actor+(3+n)*64,ngb_fast_ram+csr-6};
    unsigned sizes[]={16,28,40,64,64,8};
    for(unsigned i=0;i<6;i++){
      uintptr_t p=(uintptr_t)inputs[i],st=(uintptr_t)stack,mat=(uintptr_t)ngb_fast_ram+0x950180,ap=(uintptr_t)ngb_fast_ram+actor+0x8cc;
      if((p<(uintptr_t)ngb_fast_ram+0xdb67c4 && p+sizes[i]>(uintptr_t)ngb_fast_ram+0xdb67c0)||(p<st+sp+112-low&&p+sizes[i]>st)||(p<mat+64&&p+sizes[i]>mat)||(p<ap+4&&p+sizes[i]>ap))return 0;
    }
    float ballv[4],bounds[7];memcpy(ballv,sph,16);memcpy(bounds,bx,28);
    typedef float V4 __attribute__((vector_size(16)));
    V4 a[4],mm[4],inv[4];float l[4][4];
    memcpy(a,ngb_fast_ram+actor,64);memcpy(&a[3],ngb_fast_ram+actor+0x8c0,12);
    float one=MEMF(0x4148c8),pad=MEMF(0x4149c4);
    memcpy(l,ngb_fast_ram+actor+(3+n)*64,64);
    V4 init[4];memcpy(init,ngb_fast_ram+0x950140,64);
    unsigned bone_addr=actor+(3+n)*64;float neg[3];
    #include "memo.inc"
    V4 center=((ballv[0]*inv[0]+inv[3])+ballv[1]*inv[1])+ballv[2]*inv[2];
    float limit=ballv[3]+pad,hi,delta;
    int hit=0;for(unsigned i=0;i<3;i++){delta=bounds[i]-center[i];hi=(bounds[4+i]+delta)+limit;if(0.f>hi){hit=1;break;}delta-=limit;if(delta>0.f){hit=1;break;}}
    if(!hit)return 0;
    uint8_t *ram=ngb_fast_ram;
    // Write the final image rather than executing intermediate guest stores.
    #define WR(at,val) do{uint32_t _v=(val);memcpy(ram+(at),&_v,4);}while(0)
    memcpy(ram+actor+0x8cc,&one,4);memcpy(ram+0x950180,inv,64);WR(0xdb67c0,0);
    memcpy(ram+sp+48,init,64);for(unsigned i=0;i<3;i++)memcpy(ram+sp+48+16*i,&mm[i],12);
    memcpy(ram+sp+32,&mm[3],12);memcpy(ram+sp+44,&one,4);
    unsigned args[9]={0x13d550,255,65535,q[0x25],ball,sp+32,sp+48,MEM32(sp+20),box};
    memcpy(ram+sp-36,args,36);
    WR(childfp,fp);WR(cs+8,csr);WR(cs+4,esi);WR(cs,actor);
    WR(cs+20,cs+48);center[3]=ballv[3];memcpy(ram+cs+48,&center,16);
    WR(cs-4,0x140b25);WR(cs-8,childfp);WR(low+8,0x9501b0);WR(low+12,low+16);memcpy(ram+low+16,neg,12);
    #undef WR
    eax=0;ecx=0x950180;edx=sp+32;edi=actor;esp=sp-32;g_ebp=g_seh_ebp=cs-8;
    xmm0=XMM_SCALAR(limit);xmm1=XMM_ZERO();xmm2=XMM_SCALAR(delta);xmm3=XMM_SCALAR(ballv[3]);xmm4=XMM_SCALAR(hi);memcpy(&xmm5,&mm[3],16);
    unsigned addr[5]={0x3059a0,0x328232,0x140af0,0x3059a0,0x3066b0};
    for(unsigned i=0;i<5;i++)ngb_reg_recent[(ngb_reg_entries+i)&31]=addr[i];
    ngb_reg_entries+=5;ngb_reg_current_va=0x3066b0;ngb_guest_polls+=6;return 1;
}
