extern uintptr_t __real_ngb_guest_scalar_fallback(uint32_t,size_t);
static _Thread_local unsigned ss_epoch=121,ss_rng=723,ss_counts[6],ss_n[6],ss_b[6],ss_cross[6];
static _Thread_local unsigned long long ss_ns[6],ss_blank[6];
static unsigned long long ss_clock(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return t.tv_sec*1000000000ull+t.tv_nsec;}
uintptr_t __wrap_ngb_guest_scalar_fallback(uint32_t va,size_t size){
 unsigned f=ss_epoch;
 if(f>=120)return __real_ngb_guest_scalar_fallback(va,size);
 unsigned i=va<4096?0:va<0x4000000?1:va>=0x80000000&&va<0x84000000?2:va>=0x84000000&&va<0x88000000?3:va>=0xf0000000?4:5;
 ss_counts[i]++;ss_rng=1664525u*ss_rng+1013904223u;unsigned k=ss_rng>>26;
 if(k==1){unsigned long long t=ss_clock();ss_blank[i]+=ss_clock()-t;ss_b[i]++;}
 if(k)return __real_ngb_guest_scalar_fallback(va,size);
 unsigned long long t=ss_clock();uintptr_t result=__real_ngb_guest_scalar_fallback(va,size);unsigned long long dt=ss_clock()-t;
 if(f==ss_epoch){ss_n[i]++;ss_ns[i]+=dt;}else ss_cross[i]++;
 return result;
}
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<6;i++)fprintf(stderr,"[SCALAR_SLOW] %u %u %u %u %llu %u %llu %u\n",f,i,ss_counts[i],ss_n[i],ss_ns[i],ss_b[i],ss_blank[i],ss_cross[i]);
 if(!f||f==30){memset(ss_counts,0,sizeof ss_counts);memset(ss_n,0,sizeof ss_n);memset(ss_b,0,sizeof ss_b);memset(ss_cross,0,sizeof ss_cross);memset(ss_ns,0,sizeof ss_ns);memset(ss_blank,0,sizeof ss_blank);}
 ss_epoch=f;
}
