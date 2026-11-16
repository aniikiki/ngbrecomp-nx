#include <time.h>
static unsigned lw_frame=999,lw_count[2],lw_n[2],lw_cross[2],lw_rng=42;
static unsigned long long lw_total[2];
static unsigned long long lw_now(void){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return (unsigned long long)t.tv_sec*1000000000+t.tv_nsec;}
unsigned long long light_begin(unsigned i){
 if(lw_frame>=120)return 0;
 ++lw_count[i];
 lw_rng=1664525u*lw_rng+1013904223u;
 if(lw_rng>>29)return 0;
 return (lw_now()<<8)|lw_frame;
}
void light_end(unsigned i,unsigned long long t){
 if(!t)return;
 if((t&255)!=lw_frame){++lw_cross[i];return;}
 lw_total[i]+=lw_now()-(t>>8);++lw_n[i];
}
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<2;i++)
 fprintf(stderr,"[LIGHT_STAGE] end=%u stage=%u count=%u sampled=%u cpu_ns=%llu crossed=%u\n",f,i,lw_count[i],lw_n[i],lw_total[i],lw_cross[i]);
 if(!f||f==30){memset(lw_count,0,sizeof lw_count);memset(lw_n,0,sizeof lw_n);memset(lw_total,0,sizeof lw_total);memset(lw_cross,0,sizeof lw_cross);}
 lw_frame=f;
}
