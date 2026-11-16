// Only the common failed type-3 equality test; a due callback falls through.
// All state changes before the parent returns are restored or reproduced.
unsigned pf_arm;static unsigned pf_hits,pf_checks;
static struct {uint32_t ax,cx,dx,sp,bx,si,di,words[11];unsigned char *r;} pf;
static int pf_page(unsigned a,unsigned n){return a<0x04000000 && n<=4096-(a&4095) && ngb_fast_page_bytes[a>>12]==4096;}
static unsigned pf_read(const void *p,unsigned n){unsigned v=0;memcpy(&v,p,n);return v;}
extern uint64_t ngb_reg_entries;extern unsigned ngb_reg_current_va,ngb_reg_recent[];
const uint32_t *pf_try(unsigned char *r,unsigned sp,unsigned cx,unsigned row,unsigned bx,unsigned si,unsigned di,unsigned bp){
 // XDK calls and scheduler callbacks keep their original path.
 if(sp<0x01000030 || (sp&3) || !pf_page(sp-44,48) || cx>=0x04000000-0x2800 || !pf_page(cx+0x277c,2)||!pf_page(cx+0x27f0,1))return 0;
 unsigned off=row&0x7fffffff; if(off>=0x08000000-8 || (row&4095)>4090 || ngb_fast_page_bytes[row>>12]!=4096)return 0;
 if((off<sp+4&&off+6>sp-44)||(cx<sp+4&&cx+0x2800>sp-44))return 0;
 unsigned t=pf_read(r+off+2,2),v=pf_read(r+off+4,2);
 if((t&255)!=3||v==pf_read(r+cx+0x277c,2)||pf_read(r+0x3b138,4)!=0x3af60)return 0;
 uint64_t next=ngb_guest_polls+1;
 if(!(next&ngb_poll_mask)||ngb_pending_dpcs||ngb_reg_entries<=47)return 0;
 // Fields follow the Xbox stack in ascending addresses from SP-44.
 unsigned table=0x4968b0+r[cx+0x27f0]*0xdd0;
 unsigned w[11]={0,row,/* saved seh ebp */bp,table,0x3b44e,t,v,di,si,bp,bx};
 // The child's saved edi is the parent's entry eax, supplied below.
 extern unsigned pf_actor;w[0]=pf_actor;
 pf.r=r;pf.ax=0;pf.cx=cx;pf.dx=3;pf.sp=sp;pf.bx=bx;pf.si=si;pf.di=di;memcpy(pf.words,w,44);
 ++pf_hits;
 if(pf_arm==1){
  ngb_reg_current_va=0x3ae90;ngb_reg_recent[ngb_reg_entries++&31]=0x3ae90;ngb_guest_polls=next;
  memcpy(r+sp-44,w,44);
 }
 return &pf.ax;
}
unsigned pf_actor;
void pf_check(unsigned sp,unsigned ax,unsigned cx,unsigned dx,unsigned bx,unsigned si,unsigned di){
 if(sp!=pf.sp+4||ax!=pf.ax||cx!=pf.cx||dx!=pf.dx||bx!=pf.bx||si!=pf.si||di!=pf.di||memcmp(pf.r+pf.sp-44,pf.words,44)){
 fprintf(stderr,"[FUSED_DIFF] sp %x/%x ax %x cx %x/%x dx %x/%x bx %x/%x si %x/%x di %x/%x\n",sp,pf.sp+4,ax,cx,pf.cx,dx,pf.dx,bx,pf.bx,si,pf.si,di,pf.di);
 for(unsigned i=0;i<11;i++){fprintf(stderr," %u:%x/%x",i,pf_read(pf.r+pf.sp-44+4*i,4),pf.words[i]);}abort();}
 ++pf_checks;
}
