static unsigned rb_on,rb_masks[64],rb_min[256],rb_max[256];
void rb_fail(const float*k,const float*r){
 if(!rb_on)return;
 unsigned mask=0,lo=255,hi=0;
 for(unsigned i=0;i<20;i++){uint32_t u;memcpy(&u,i<4?k+i:r+i-4,4);u&=0x7fffffffu;
 if(!u)continue;
 unsigned e=u>>23;if(e<lo)lo=e;if(e>hi)hi=e;
 unsigned bit=e==255?4:u>(157u<<23)?2:u<(97u<<23)?1:0;
 mask|=bit<<(i<4?0:3);}
 rb_masks[mask]++;rb_min[lo]++;rb_max[hi]++;
}
void phase_flip(unsigned f){
 if(f==30||f==120){
 for(unsigned i=0;i<64;i++)if(rb_masks[i])fprintf(stderr,"[ROW_BINS] %u mask %u %u\n",f,i,rb_masks[i]);
 for(unsigned i=0;i<256;i++)if(rb_min[i]||rb_max[i])fprintf(stderr,"[ROW_BINS] %u exp %u %u %u\n",f,i,rb_min[i],rb_max[i]);}
 if(!f||f==30){memset(rb_masks,0,sizeof rb_masks);memset(rb_min,0,sizeof rb_min);memset(rb_max,0,sizeof rb_max);}
 rb_on=f<120;
}
