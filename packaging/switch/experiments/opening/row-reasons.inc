unsigned rr_on,rr_counts[2][6];
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned c=0;c<2;c++)for(unsigned i=0;i<6;i++)fprintf(stderr,"[ROW_REASONS] %u %u %u %u\n",f,c,i,rr_counts[c][i]);
 if(!f||f==30)memset(rr_counts,0,sizeof rr_counts);
 rr_on=f<120;
}
