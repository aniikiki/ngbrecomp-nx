static unsigned mc_on,mc_keys[256],mc_totals[256],mc_used,mc_overflow;
void mc_target(unsigned target){if(!mc_on)return;unsigned n=0;for(;n<mc_used;n++)if(mc_keys[n]==target)break;
 if(n==256){mc_overflow++;return;}if(n==mc_used)mc_keys[mc_used++]=target;mc_totals[n]++;}
static void mc_flip(unsigned f){if(f==30||f==120){fprintf(stderr,"[MAT_TARGET] %u overflow=%u",f,mc_overflow);
 for(unsigned i=0;i<mc_used;i++){fprintf(stderr," %x:%u",mc_keys[i],mc_totals[i]);}fputc(10,stderr);}
 if(!f||f==30){mc_used=mc_overflow=0;memset(mc_totals,0,sizeof mc_totals);}mc_on=f<120;}
