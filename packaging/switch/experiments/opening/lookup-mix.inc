extern void (*__real_recomp_lookup(uint32_t))(void);
static _Thread_local unsigned lm_on,lm_keys[8192],lm_counts[8192],lm_total,lm_full,lm_hits,lm_recent[256];
void (*__wrap_recomp_lookup(uint32_t va))(void){
 if(lm_on){
  unsigned j=(va*2654435761u)>>19,slot=(va^(va>>8))&255;
  lm_total++;lm_hits+=lm_recent[slot]==va && va!=0;lm_recent[slot]=va;
  unsigned i=0;for(;i<8192;i++,j=(j+1)&8191){
   if(!lm_counts[j]||lm_keys[j]==va){lm_keys[j]=va;lm_counts[j]++;break;}
  }
  lm_full+=i==8192;
 }
 return __real_recomp_lookup(va);
}
void phase_flip(unsigned f){
 if(f==30||f==120){
  fprintf(stderr,"[LOOKUP_MIX] %u calls=%u same_slot=%u full=%u\n",f,lm_total,lm_hits,lm_full);
  for(unsigned j=0;j<8192;j++)if(lm_counts[j])fprintf(stderr,"[LOOKUP_KEY] %u %x %u\n",f,lm_keys[j],lm_counts[j]);
 }
 if(!f||f==30){lm_total=lm_hits=lm_full=0;memset(lm_counts,0,sizeof lm_counts);memset(lm_recent,0,sizeof lm_recent);}
 lm_on=f<120;
}
