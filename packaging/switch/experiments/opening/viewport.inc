// Same private ABI entry after the original poll. Restrict all writes to the
// known caller's ordinary stack and require the device and stack not to alias.
static struct {uint32_t key[18],top; uint8_t locals[16],out[32];uint64_t fp[3];
 uint32_t ax,dx;int valid;} vp;
static unsigned vp_track,vp_match,vp_sp,vp_si,vp_di,vp_calls,vp_hits,vp_checked;
static uint8_t *vp_ram;
static int vp_page(uint32_t a,unsigned len){return a<0x04000000 && (a&4095)+len<=ngb_fast_page_bytes[a>>12];}
int vp_before(unsigned char *ram,uint32_t sp,uint32_t cx,uint32_t dx,uint32_t si,uint32_t di){
 vp_track=0;
 if(sp<0x01001000||sp>=0x03dfe000||!vp_page(sp-24,68)||cx!=sp+28||dx!=sp+12)return 0;
 uint32_t ret,dev;
 memcpy(&ret,ram+sp,4);if(ret!=0x3c6123)return 0;
 memcpy(&dev,ram+0x3d83c8,4);
 if(dev>=0x04000000-0xf00 || (dev<sp+44 && dev+0xf00>sp-24) ||
 !vp_page(dev+8,4)||!vp_page(dev+0x948,4)||!vp_page(dev+0x95c,8)||!vp_page(dev+0xee0,32))return 0;
 uint32_t key[18];
 memcpy(key,ram+dev+0xee0,32);memcpy(key+8,ram+dev+0x95c,8);memcpy(key+10,ram+dev+0x948,4);
 memcpy(key+11,ram+dev+8,4);memcpy(key+12,ram+0x3d8638,4);
 memcpy(key+13,ram+0x4148e4,8);memcpy(key+15,ram+0x4148c0,4);
 key[16]=g_fp_control_word;uint64_t fpcr;__asm__("mrs %0,fpcr":"=r"(fpcr));key[17]=(uint32_t)fpcr;
 unsigned top=g_fp_top;vp_match=vp.valid && vp.top==top && !memcmp(key,vp.key,sizeof key);
 ++vp_calls;vp_hits+=vp_match;vp_sp=sp;vp_ram=ram;vp_si=si;vp_di=di;
 if(vp_match && vs_arm==1){
  memcpy(ram+sp-24,&di,4);memcpy(ram+sp-20,&si,4);memcpy(ram+sp-16,vp.locals,16);
  memcpy(ram+sp+12,vp.out,32);
  for(unsigned j=0;j<3;j++)memcpy(&g_fp_stack[(top-1-j)&7],vp.fp+j,8);
  return 1;
 }
 vp_track=1;
 if(!vp_match){memcpy(vp.key,key,sizeof key);vp.top=top;vp.valid=0;}
 return 0;
}
uint32_t vp_ax, vp_dx;
void vp_after(unsigned ax,unsigned dx,unsigned cx,unsigned sp,unsigned si,unsigned di){
 if(!vp_track)return;
 vp_track=0;uint8_t *stack=vp_ram+vp_sp;
 if(sp!=vp_sp+4||cx!=vp_sp+28||si!=vp_si||di!=vp_di||memcmp(stack-24,&di,4)||memcmp(stack-20,&si,4)||vp.top!=(unsigned)g_fp_top)abort();
 uint64_t fp[3];
 for(unsigned j=0;j<3;j++)memcpy(fp+j,&g_fp_stack[(vp.top-1-j)&7],8);
 if(vp_match){
  if(ax!=vp.ax||dx!=vp.dx||memcmp(vp.locals,stack-16,16)||memcmp(vp.out,stack+12,32)||memcmp(vp.fp,fp,24))abort();
  ++vp_checked;
 }else{
  vp.ax=vp_ax=ax;vp.dx=vp_dx=dx;
  memcpy(vp.locals,stack-16,16);memcpy(vp.out,stack+12,32);memcpy(vp.fp,fp,24);vp.valid=1;
 }
}
