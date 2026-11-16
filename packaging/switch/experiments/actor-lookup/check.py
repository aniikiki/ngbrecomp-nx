"""Run original and batched generated loops; mutate lists at poll boundaries."""
from pathlib import Path
import subprocess as sp
base=Path('/work/build/switch-runtime');d=base/'core-perf/actor-lookup'
def loop(s):
 a=s.index('loc_001CBF20:');b=s.index('loc_001CBF32:',a)
 return s[a:b]+ 'loc_001CBF32: return esi;'
stub=r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static uint32_t edi,esi,ebx,ngb_poll_mask,ngb_pending_dpcs,lookup_nodes,trial_variant=1;
static uint64_t ngb_guest_polls,signature;static unsigned calls;
static uint32_t ram[4096],initial[4096];static unsigned char*ngb_fast_ram=(unsigned char*)ram;
static uint16_t ngb_fast_page_bytes[4];
#define MEM32(a) ram[(a)/4]
#define CMP_AE(a,b) ((a)>=(b))
#define CMP_EQ(a,b) ((a)==(b))
#define CMP_NE(a,b) ((a)!=(b))
static void ngb_guest_block_poll(void){
 ++ngb_guest_polls;if(!(ngb_guest_polls & ngb_poll_mask)||ngb_pending_dpcs){
 signature=signature*1315423911u+esi*19+ngb_guest_polls;calls++;ngb_pending_dpcs=0;
 if((calls&3)==1)MEM32(esi+12)^=1;else if((calls&3)==2)MEM32(esi+4)=0;
 }}
'''
s=stub
for name,p in [('ref',base/'gen/recomp_0016.c'),('alt',d/'fast.c')]:
 s+='static uint32_t '+name+'(void){unsigned _fa,_fb;int32_t _fas,_fbs;'+loop(p.read_text())+'}\n'
s+=r'''
int main(void){for(unsigned i=0;i<40000;i++){
 for(unsigned j=0;j<384;j++){unsigned a=3840+j*16;initial[(a+12)/4]=j*2;initial[(a+4)/4]=j==383?0:a+16;}
 uint32_t result=0,refcalls=0;uint64_t refsig=0,refpolls=0;static uint32_t refram[4096];
 for(unsigned v=0;v<2;v++){memcpy(ram,initial,sizeof ram);esi=3840;ebx=(i*257)%771;
 ngb_poll_mask=i%7==0?18:(1u<<(i%11))-1;ngb_guest_polls=(uint64_t)i*13;
 if(i%151==0)ngb_guest_polls+=UINT64_MAX-500;
 ngb_fast_page_bytes[0]=i%8?4096:0;ngb_fast_page_bytes[1]=i%13?4096:3000;ngb_fast_page_bytes[2]=4096;
 ngb_pending_dpcs=(i%3==0);signature=0;calls=0;
 uint32_t k=v?alt():ref();if(!v){result=k;refsig=signature;refcalls=calls;refpolls=ngb_guest_polls;memcpy(refram,ram,sizeof ram);}
 else if(k!=result||refsig!=signature||calls!=refcalls||refpolls!=ngb_guest_polls||memcmp(refram,ram,sizeof ram)){printf("mismatch %u\n",i);return 1;}
 }}printf("40000 exact loop comparisons; %u batched nodes\n",lookup_nodes);return !lookup_nodes;}
'''
f=d/'check.c';f.write_text(s);sp.run(['cc','-O2',f,'-o',d/'check'],check=True);sp.run([d/'check'],check=True)
