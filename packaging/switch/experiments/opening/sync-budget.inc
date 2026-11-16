#include <time.h>
static unsigned sb_frame=999,sb_count,sb_n[7],sb_rng=43;
static unsigned long long sb_total[7];
unsigned sb_pick(void){
 if(sb_frame>=120)return 99;
 ++sb_count; sb_rng=1664525u*sb_rng+1013904223u;
 return sb_rng>>28;
}
unsigned long long sb_now(void){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return (unsigned long long)t.tv_sec*1000000000+t.tv_nsec;}
void sb_end(unsigned j,unsigned long long t){sb_total[j]+=sb_now()-t;++sb_n[j];}
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned j=0;j<7;j++)fprintf(stderr,"[SYNC_BUDGET] end=%u calls=%u section=%u n=%u ns=%llu\n",f,sb_count,j,sb_n[j],sb_total[j]);
 if(!f||f==30){sb_count=0;memset(sb_n,0,sizeof sb_n);memset(sb_total,0,sizeof sb_total);}
 sb_frame=f;
}
