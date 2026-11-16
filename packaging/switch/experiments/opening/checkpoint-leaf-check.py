"""Run both ARM assembly checkpoints under the same synthetic ticket stream."""
from pathlib import Path
import runpy, tempfile, subprocess, sys
p=Path(__file__).resolve().parent
asm=(p.parents[1]/'arm-registers/checkpoint.S').read_text()
emit=runpy.run_path(str(p/(sys.argv[1] if len(sys.argv)>1 else 'checkpoint-leaf.py')))['emit']
gates=Path('build/switch-runtime/core-perf/opening-full-guest/gates.S').read_text()
gate='ngb_gate_ngb_poll_due'
gate=gates[gates.index(gate+':'):gates.index('.size '+gate+',')]
driver=r'''
#include <stdint.h>
#include <stdio.h>
uint64_t ngb_reg_entries,ngb_guest_polls,trace;
unsigned ngb_reg_current_va,ngb_reg_recent[32],ngb_poll_mask,ngb_pending_dpcs,regs[7];
void ngb_poll_due(uint64_t ticket){trace=trace*131+ticket;for(int i=0;i<7;i++)regs[i]+=i+1;}
void ngb_checkpoint(unsigned va){ngb_reg_current_va=va;ngb_reg_recent[ngb_reg_entries++%32]=va;
 trace=trace*131+va;if(!(++ngb_guest_polls&ngb_poll_mask)||ngb_pending_dpcs)ngb_poll_due(ngb_guest_polls);}
void invoke(unsigned);
int main(void){unsigned seed=11;for(unsigned i=0;i<120000;i++){
 seed=seed*1664525+1013904223;unsigned v=seed&0x3fffff;
 if(i%179==0)v=0x17a010;if(i%193==0)v=0x31dc50;if(i%227==0)v=0x3cc310;
 ngb_pending_dpcs=i%111==0;ngb_poll_mask=(i&4096)?63:255;
 invoke(v);trace=trace*131+ngb_reg_current_va+ngb_reg_entries+ngb_guest_polls+ngb_reg_recent[(ngb_reg_entries-1)%32];}
 printf("%llu ",(unsigned long long)trace);for(int i=0;i<7;i++)printf("%u ",regs[i]);}
'''
wrapper='''
.text
.global invoke
invoke:
 stp x29,x30,[sp,-96]!
 stp x19,x20,[sp,16]
 stp x21,x22,[sp,32]
 stp x23,x24,[sp,48]
 stp x25,x28,[sp,64]
 adrp x28,regs
 add x28,x28,:lo12:regs
 ldp w19,w20,[x28]
 ldp w21,w22,[x28,8]
 ldp w23,w24,[x28,16]
 ldr w25,[x28,24]
 bl ngb_reg_checkpoint
 stp w19,w20,[x28]
 stp w21,w22,[x28,8]
 stp w23,w24,[x28,16]
 str w25,[x28,24]
 ldp x25,x28,[sp,64]
 ldp x23,x24,[sp,48]
 ldp x21,x22,[sp,32]
 ldp x19,x20,[sp,16]
 ldp x29,x30,[sp],96
 ret
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);f=d/'main.c';f.write_text(driver)
 outputs=[]
 for s in (asm,emit(asm)):
    if '.data.opening_counters' in s:
        f.write_text(driver.replace('uint64_t ngb_reg_entries,ngb_guest_polls,trace;', 'extern uint64_t ngb_reg_entries,ngb_guest_polls; uint64_t trace;').replace('unsigned ngb_reg_current_va,ngb_reg_recent[32],ngb_poll_mask,ngb_pending_dpcs,regs[7];','extern unsigned ngb_reg_current_va,ngb_reg_recent[32],ngb_poll_mask,ngb_pending_dpcs; unsigned regs[7];'))
    a=d/'check.S';a.write_text(s+wrapper+gate)
    e=d/'check';subprocess.run(['cc','-O2','-no-pie',f,a,'-o',e],check=True)
    outputs.append(subprocess.check_output([e]))
 assert outputs[0]==outputs[1],outputs
 print('120000 entry stream matched incl startup, periodic/pending callbacks and all 7 guest registers')
