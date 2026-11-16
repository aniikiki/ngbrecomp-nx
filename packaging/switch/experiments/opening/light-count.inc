unsigned lc_on,lc_va[8],lc_calls[8],lc_fast[8];unsigned long long lc_words[8];
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<8;i++)fprintf(stderr,"[LIGHT_COUNT] %u %u %x %u %u %llu\n",f,i,lc_va[i],lc_calls[i],lc_fast[i],lc_words[i]);
 if(!f||f==30){memset(lc_calls,0,sizeof lc_calls);memset(lc_fast,0,sizeof lc_fast);memset(lc_words,0,sizeof lc_words);}
 lc_on=f<120;
}
