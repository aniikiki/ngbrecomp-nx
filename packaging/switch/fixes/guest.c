#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#define RECOMP_GENERATED_CODE
#include "recomp_funcs.h"
RECOMP_TLS RecompRegs g_regs;
unsigned char *ngb_fast_ram;
uint16_t ngb_fast_page_bytes[1u<<20];
uintptr_t ngb_guest_scalar_fallback(uint32_t a,size_t n){assert(a+n<0x1000000);return (uintptr_t)(ngb_fast_ram+a);}
uintptr_t ngb_guest_pointer(uint32_t a,size_t n){return ngb_guest_scalar_fallback(a,n);}
static unsigned unlocked,selected,drawn,sprite;
int ngb_unlock(int id){assert(!id);return unlocked;}
static void call(unsigned addr){
 switch(addr){
 case 0x1744F0:sprite=ecx;break; // sprite initializer
 case 0x221340:drawn++;break; // submit sprite
 case 0x176070:eax=selected;break; // selected row
 case 0x1E3400:break; // sound
 case 0x177330:case 0x17A250:break; // rebuild menu widget
 default:fprintf(stderr,"unexpected call %x\n",addr);abort();
 }
 esp+=4;
}
#undef RECOMP_ABI_CALL
#define RECOMP_ABI_CALL(addr,fn) call(addr)
#undef RECOMP_ENTRY
#define RECOMP_ENTRY(addr) ((void)0)
#undef RECOMP_ICALL_SAFE_AT
#define RECOMP_ICALL_SAFE_AT(addr,sp0,site) do{esp=sp0;eax=9;}while(0)
#include "handlers.inc"
static void check(unsigned on,unsigned earned,unsigned top,unsigned expected){
 unlocked=on;selected=38;memset(ngb_fast_ram,0,0x1000000);
 ebx=0x40000;esp=0x110000;MEM32(ebx+0xCC)=0x50000;MEM32(0xD219A8)=0x10;
 MEM8(0xDB95AC+selected)=earned;MEM8(0xDB9610+selected)=top;
 sub_00176E30();
 assert(esp==0x110008 && MEM8(0xDB95AC+selected)==earned && MEM8(0xDB9610+selected)==top);
 assert(MEM8(0x589755)==expected);
 if(expected>1){
   assert(MEM8(0x589758)==selected && MEM32(ebx+0xC)==2);
   for(int i=1;i<=4;i++) assert(MEM8(0x50004+i*8)==(i<=expected) && MEM8(0x50005+i*8)==(i<=expected));
 }
}
int main(void){
 ngb_fast_ram=calloc(1,0x1000000);
 check(0,0,0,0);check(1,0,0,4);check(0,3,2,2);check(1,3,2,4);check(0,3,4,4);check(0,1,1,1);
 for(int i=0;i<16;i++){
   esp=0x110000;eax=0;MEM32(esp+4)=0x60000;MEM32(esp+8)=0;MEM32(0x60000)=i;
   drawn=sprite=0;sub_001EAA10();int j=i-(i<10?2:12);
   assert(esp==0x110004 && drawn==(j>=0) && sprite==(j>=0?0x1d6+j:0));
 }
 puts("PASS: six mission confirm states, save bytes unchanged, 16 technique-icon decisions");
}
