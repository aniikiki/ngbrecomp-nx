unsigned tree_epoch=121;
static unsigned tc_rng=233,tc_calls[2],tc_samples[2],tc_blanks[2],tc_cross[2];
static unsigned long long tc_ns[2],tc_blank[2];
static unsigned long long tc_clock(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return t.tv_sec*1000000000ull+t.tv_nsec;}
unsigned long long tree_begin(unsigned i){
 if(tree_epoch>=120)return 0;
 tc_calls[i]++;tc_rng=tc_rng*1664525u+1013904223u;unsigned k=tc_rng>>28;
 if(k==0)return tc_clock();
 if(k==1){unsigned long long t=tc_clock();tc_blank[i]+=tc_clock()-t;tc_blanks[i]++;}
 return 0;
}
void tree_end(unsigned i,unsigned f,unsigned long long t){
 if(f!=tree_epoch){tc_cross[i]++;return;}
 tc_ns[i]+=tc_clock()-t;tc_samples[i]++;
}
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<2;i++)fprintf(stderr,"[TREE_COST] %u %u calls=%u samples=%u ns=%llu blanks=%u blank_ns=%llu cross=%u\n",f,i,tc_calls[i],tc_samples[i],tc_ns[i],tc_blanks[i],tc_blank[i],tc_cross[i]);
 if(!f||f==30){memset(tc_calls,0,sizeof tc_calls);memset(tc_samples,0,sizeof tc_samples);memset(tc_ns,0,sizeof tc_ns);memset(tc_blanks,0,sizeof tc_blanks);memset(tc_blank,0,sizeof tc_blank);memset(tc_cross,0,sizeof tc_cross);}
 tree_epoch=f;
}
