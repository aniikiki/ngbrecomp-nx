static unsigned gap_frame,gap_calls,gap_draws,gap_bins[5],gap_saved[5],gap_has;
static size_t gap_end;
void gap_reset(void){gap_has=0;if(gap_frame)++gap_draws;}
void gap_write(size_t off,size_t len){
 if(!gap_frame)return;
 ++gap_calls;
 if(gap_has && off>=gap_end){
  size_t gap=off-gap_end;unsigned k=gap==0?0:gap<=8?1:gap<=32?2:gap<=64?3:4;
  ++gap_bins[k];if(k<4)gap_saved[k]+=gap;
 }
 gap_has=1;gap_end=off+len;
}
void phase_flip(unsigned f){
 if(f==30||f==120){fprintf(stderr,"[DELTA_GAP] %u %u %u",f,gap_draws,gap_calls);
  for(unsigned i=0;i<5;i++){fprintf(stderr," %u:%u",gap_bins[i],gap_saved[i]);}fputc(10,stderr);}
 if(!f||f==30){gap_draws=gap_calls=0;memset(gap_bins,0,sizeof gap_bins);memset(gap_saved,0,sizeof gap_saved);}
 gap_frame=f<120?f+1:0;gap_has=0;
}
