static unsigned sep_frame,sep_bins[257][2];
unsigned draw_sep_epoch(void){return sep_frame;}
void draw_sep_pair(unsigned m,unsigned idx){if(m>256||idx>1)abort();++sep_bins[m][idx];}
static unsigned sep_shader_counts[64];
void draw_sep_shader(unsigned k){if(!k||k>=64)abort();++sep_shader_counts[k];}
static unsigned sep_strip[8];
void sep_strip_reason(unsigned r){if(!r||r>7)abort();++sep_strip[r];}
static unsigned sep_bounds[16];
void sep_footprint(unsigned k){if(k>=16)abort();++sep_bounds[k];}
void phase_flip(unsigned f){
 if(f==30||f==120){
  for(unsigned m=0;m<=256;m++)if(sep_bins[m][0]||sep_bins[m][1])
   fprintf(stderr,"[DRAW_SEP] %u %u %u %u\n",f,m,sep_bins[m][0],sep_bins[m][1]);
  for(unsigned k=1;k<64;k++)if(sep_shader_counts[k])fprintf(stderr,"[DRAW_SHADER] %u %u %u\n",f,k,sep_shader_counts[k]);
  memset(sep_shader_counts,0,sizeof sep_shader_counts);
  for(unsigned r=1;r<=7;r++)if(sep_strip[r])fprintf(stderr,"[STRIP_REASON] %u %u %u\n",f,r,sep_strip[r]);
  for(unsigned k=0;k<16;k++)if(sep_bounds[k])fprintf(stderr,"[STRIP_FOOTPRINT] %u %u %u\n",f,k,sep_bounds[k]);
  memset(sep_bounds,0,sizeof sep_bounds);
  memset(sep_strip,0,sizeof sep_strip);
  memset(sep_bins,0,sizeof sep_bins);
 }
 sep_frame=f<120?f+1:0;
}
