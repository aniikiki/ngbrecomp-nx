unsigned aq_epoch=121,aq_counts[5];
static unsigned aq_rng=331,aq_n,aq_b,aq_cross;
static unsigned long long aq_ns,aq_empty;
static unsigned long long aq_clock(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return t.tv_sec*1000000000ull+t.tv_nsec;}
unsigned long long aq_begin(void){
 if(aq_epoch>=120)return 0;
 aq_counts[0]++;aq_rng=aq_rng*1664525u+1013904223u;
 switch(aq_rng>>27){case 0:return aq_clock();case 1:{unsigned long long t=aq_clock();aq_empty+=aq_clock()-t;aq_b++;break;}}
 return 0;
}
void aq_end(unsigned f,unsigned long long t){if(f!=aq_epoch){aq_cross++;return;}aq_ns+=aq_clock()-t;aq_n++;}
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[AXIS_QUERY] %u calls=%u y=%u z=%u next=%u reject_exit=%u ns=%llu n=%u blank=%llu b=%u cross=%u\n",f,aq_counts[0],aq_counts[1],aq_counts[2],aq_counts[3],aq_counts[4],aq_ns,aq_n,aq_empty,aq_b,aq_cross);
 if(!f||f==30){memset(aq_counts,0,sizeof aq_counts);aq_ns=aq_n=aq_empty=aq_b=aq_cross=0;}
 aq_epoch=f;
}
