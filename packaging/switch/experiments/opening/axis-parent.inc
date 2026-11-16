unsigned ap_epoch=121;
static unsigned ap_rng=773,ap_calls[13],ap_n[13],ap_b[13],ap_cross[13];
static unsigned long long ap_ns[13],ap_empty[13];
static unsigned long long ap_clock(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return t.tv_sec*1000000000ull+t.tv_nsec;}
unsigned long long ap_begin(unsigned i){
 if(ap_epoch>=120)return 0;
 ap_calls[i]++;ap_rng=1664525u*ap_rng+1013904223u;unsigned k=ap_rng>>27;
 if(!k)return ap_clock();
 if(k==1){unsigned long long t=ap_clock();ap_empty[i]+=ap_clock()-t;ap_b[i]++;}
 return 0;
}
void ap_end(unsigned i,unsigned f,unsigned long long t){
 if(ap_epoch!=f){ap_cross[i]++;return;}ap_ns[i]+=ap_clock()-t;ap_n[i]++;
}
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<13;i++)fprintf(stderr,"[AXIS_PARENT] %u %u %u %u %llu %u %llu %u\n",f,i,ap_calls[i],ap_n[i],ap_ns[i],ap_b[i],ap_empty[i],ap_cross[i]);
 if(!f||f==30){memset(ap_calls,0,sizeof ap_calls);memset(ap_n,0,sizeof ap_n);memset(ap_ns,0,sizeof ap_ns);memset(ap_b,0,sizeof ap_b);memset(ap_empty,0,sizeof ap_empty);memset(ap_cross,0,sizeof ap_cross);}
 ap_epoch=f;
}
