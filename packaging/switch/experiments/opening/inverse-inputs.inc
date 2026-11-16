unsigned stream_on;
static uint32_t last_va, can_compare, last_words[20],inverse_seen,inverse_ok,inverse_same,inverse_full;
static struct {uint32_t used,words[20];} inverse_keys[2048];
static int inv_readable(uint32_t a,unsigned n,const uint32_t *ends){
 return a<=64u*1024u*1024u-n && a+n-4u<ends[a>>12];
}
void stream_visit(unsigned va,unsigned sp,const uint8_t *ram,const uint32_t *ends,unsigned ecx,unsigned edx){
 uint32_t ret=0;
 if((va==0x3059a0 || va==0x3066b0) && inv_readable(sp,4,ends))memcpy(&ret,ram+sp,4);
 if(va==0x3059a0){
  can_compare=ret==0x140b20 && inv_readable(ecx,64,ends) && inv_readable(edx,12,ends) && inv_readable(0x4148c8,4,ends);
  if(can_compare){
   memcpy(last_words,ram+ecx,64); memcpy(last_words+16,ram+edx,12);memcpy(last_words+19,ram+0x4148c8,4);
  }
 }
 if(va==0x3066b0 && ret==0x140b25){
  ++inverse_seen;
  if(last_va==0x3059a0 && can_compare){
   ++inverse_ok;
   unsigned h=2166136261u;
   for(unsigned i=0;i<20;i++)h=(h^last_words[i])*16777619u;
   for(unsigned i=0;i<2048;i++){
    unsigned j=(h+i)&2047;
    if(!inverse_keys[j].used){inverse_keys[j].used=1;memcpy(inverse_keys[j].words,last_words,80);break;}
    if(!memcmp(inverse_keys[j].words,last_words,80)){++inverse_same;break;}
    if(i==2047)++inverse_full;
   }
  }
 }
 last_va=va;
}
void phase_flip(unsigned f){
 if(f==30||f==120){fprintf(stderr,"[INVERSE_INPUTS] %u %u %u %u %u\n",f,inverse_seen,inverse_ok,inverse_same,inverse_full);
  inverse_seen=inverse_ok=inverse_same=inverse_full=0;}
 memset(inverse_keys,0,sizeof inverse_keys);last_va=can_compare=0;stream_on=f<120;
}
