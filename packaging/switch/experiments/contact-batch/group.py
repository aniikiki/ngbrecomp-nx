"""Fuse certified consecutive misses across candidates up to the next true
interrupt. Materialize only the last candidate; retain all eip/ticket slots.
Experimental headroom trial: DO NOT enable without whole-group shadow tests."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
p=Path('/work/build/switch-runtime');d=p/'opt050/contact-batch';d.mkdir(exist_ok=True)
leaf=(here/'leaf.h').read_text().replace('#include "memo.inc"',(here/'memo.inc').read_text())
check=(here/'check.inc').read_text()
group=r"""
static inline unsigned contact_group(unsigned fp){
 unsigned sp=esp,node=ebx,actor_query=esi;
 if(sp<0x1001000||sp>=0x3dfe000||(sp&3)||!ngb_ram_span(sp-256,400)||ngb_pending_dpcs||ngb_reg_entries<48)return 0;
 unsigned i=MEM32(sp+24),end=MEM32(0xbbba28);
 if(end>256 || i>=end || node!=0x7a79c6u+8u*i || MEM32(sp+28)!=sp+48)return 0;
 unsigned capacity=(ngb_poll_mask-(ngb_guest_polls&ngb_poll_mask)+1)/7;
 if(capacity<2)return 0;
 unsigned n=0; if(capacity>end-i)capacity=end-i;
 for(;n<capacity;n++){
  unsigned x=node+8*n,actor=0x4b4e50+MEM8(x)*0x2800u;
  // Each retirement overwrites pose.w, the current matrix, DB67C0 and
  // the temporary/argument stack. None may contain later query inputs.
  if(actor>=0x7a0000||MEM16(x-2)>=31||!ngb_ram_span(actor_query,40))break;
  unsigned sv=MEM32(actor_query),box=MEM32(x-6);
  if(box>0xffffffd0u)break;
  const void*pa=ngb_ram_span(sv,16),*pb=ngb_ram_span(box+16,28);
  if(!pa||!pb)break;
  const void*inputs[]={pa,pb,ngb_ram_span(actor_query,40)};
  unsigned lens[]={16,28,40};int safe=1;
  for(int j=0;j<3;j++){
   uintptr_t addr=(uintptr_t)inputs[j]-(uintptr_t)ngb_fast_ram;
   // Limit ranges to non-overlapping known ROM image, actor or ordinary
   // committed game data; never permit an earlier actor.w overwrite.
   if((addr<sp+112 && addr+lens[j]>sp-256)||(addr<0x9501c0 && addr+lens[j]>0x950180)||
      (addr<0xdb67c4 && addr+lens[j]>0xdb67c0))safe=0;
   for(unsigned k=0;k<=n;k++){unsigned w=0x4b4e50+MEM8(node+8*k)*0x2800u+0x8cc;if(addr<w+4 && addr+lens[j]>w)safe=0;}
  }
  if(!safe||!predict_box(x,actor_query))break;
 }
 if(n<2)return 0;
 // Execute the final candidate with its exact frame/stack state. If the
 // exact predicate fails, restore preflight temporaries and fall back.
 unsigned last=node+8*(n-1);
 ebx=last;
 if(!contact_leaf(fp)){ebx=node;return 0;}
 // Five original entry records per miss, with the same recurring order.
 unsigned pcs[]={0x3059a0,0x328232,0x140af0,0x3059a0,0x3066b0};
 uint32_t one=MEM32(0x4148c8);
 for(unsigned k=0;k<n-1;k++){
  unsigned obj=0x4b4e50+MEM8(node+8*k)*0x2800u;
  memcpy(ngb_fast_ram+obj+0x8cc,&one,4);
  for(unsigned j=0;j<5;j++)ngb_reg_recent[(ngb_reg_entries+j)&31]=pcs[j];
  ngb_reg_entries+=5;
 }
 ngb_guest_polls+=7*(n-1);MEM32(sp+24)=i+n-1;
 return n;
}
"""
src=(p/'gen/recomp_0009.c').read_text();tag='void sub_0013D330(void)\n{'
src=src.replace(tag,'extern unsigned ngb_reg_recent[32],ngb_reg_current_va;extern uint64_t ngb_reg_entries;\n'+leaf+'\n'+check+'\n'+group+'\n'+tag)
k='loc_0013D410: ; ngb_guest_block_poll();'
src=src.replace(k,k+' if(contact_group(ebp) || contact_leaf(ebp))goto loc_0013D550;')
(d/'fast.c').write_text(src)
q=(here/'leaf.py').read_text();q=q[q.index(" abi=Path('/work/packaging/switch/arm-registers')"):]
import textwrap
q=textwrap.dedent(q).replace('opt050/contact-leaf','opt050/contact-batch');exec(q)
