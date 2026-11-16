unsigned pred_arm;
static unsigned pn_hits,pn_checked;
static struct {unsigned sp,ax,cx,dx,bx,si,di,words[4];unsigned char *ram;} plan;
static int page_ok(unsigned a,unsigned n){return a<0x04000000u && n<=4096-(a&4095) && ngb_fast_page_bytes[a>>12]==4096;}
static uint32_t word(const void *a){uint32_t v;memcpy(&v,a,4);return v;}
static uint32_t half(const void *a){uint16_t v;memcpy(&v,a,2);return v;}
const unsigned *pred_compute(unsigned char *r,unsigned sp,unsigned cx,unsigned dx,unsigned bx,unsigned si,unsigned di,unsigned bp){
 if(dx || sp<0x01000010u || !page_ok(sp-16,28) || (sp&3) || word(r+sp)!=0x3b44e || cx>=0x04000000-0x2800 || (cx<sp+12 && cx+0x2800>sp-16) || !page_ok(cx+0x27f0,1))return 0;
 unsigned kind=word(r+sp+4)&255, val=word(r+sp+8),res,source=0,n=0,next=cx,dxout=kind;
 switch(kind){
 case 0:res=1;break;
 case 1:source=cx+0x2799;n=1;break;
 case 2:source=cx+0x279c;n=1;break;
 case 3:case 7:source=cx+0x277c;n=2;break;
 case 4:source=0x4968b0+r[cx+0x27f0]*0xdd0+4;n=1;break;
 case 18:source=cx+0x2774;n=2;break;
 default:if(kind<=18)return 0;res=0;break;
 }
 if(kind<=18){
 static const unsigned target[19]={[0]=0x3b0d2,[1]=0x3af44,[2]=0x3af52,[3]=0x3af60,[4]=0x3af6c,[7]=0x3af60,[18]=0x3b0c7};
 if(word(r+0x3b12c+kind*4)!=target[kind])return 0;
 }
 if(n){if(!page_ok(source,n))return 0;unsigned v=n==1?r[source]:half(r+source);res=val==v;
 if(kind==1||kind==4)next=v;
 if(kind==2)dxout=v;}
 ++pn_hits;plan.sp=sp;plan.ram=r;plan.ax=res;plan.cx=next;plan.dx=dxout;plan.bx=bx;plan.si=si;plan.di=di;
 plan.words[0]=di;plan.words[1]=si;plan.words[2]=bp;plan.words[3]=bx;
 if(pred_arm==1)memcpy(r+sp-16,plan.words,16);
 return &plan.ax;
}
void pred_check(unsigned sp,unsigned ax,unsigned cx,unsigned dx,unsigned bx,unsigned si,unsigned di){
 if(sp!=plan.sp+4 || ax!=plan.ax||cx!=plan.cx||dx!=plan.dx||bx!=plan.bx||si!=plan.si||di!=plan.di||memcmp(plan.ram+plan.sp-16,plan.words,16))abort();
 ++pn_checked;
}
