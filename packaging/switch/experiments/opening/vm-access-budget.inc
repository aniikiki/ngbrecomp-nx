static _Thread_local unsigned vb_on,vb_rng;
static _Thread_local uint64_t vb_calls,vb_single,vb_multi,vb_pages,vb_invalid,vb_n[2],vb_time[2];
extern int __real_ngb_vm_access(uint32_t,size_t);
static uint64_t vb_tick(void){struct timespec ts;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&ts))abort();return (uint64_t)ts.tv_sec*1000000000+ts.tv_nsec;}
int __wrap_ngb_vm_access(uint32_t a,size_t n){
 if(!vb_on)return __real_ngb_vm_access(a,n);
 vb_calls++;vb_rng=vb_rng*1664525u+1013904223u;
 unsigned r=vb_rng>>26;uint64_t t=0;
 if(r==1){t=vb_tick();vb_time[1]+=vb_tick()-t;vb_n[1]++;}
 if(r==0)t=vb_tick();
 int ok=__real_ngb_vm_access(a,n);
 if(r==0){vb_time[0]+=vb_tick()-t;vb_n[0]++;}
 if(ok){uint64_t p=((a&4095u)+(uint64_t)n+4095)/4096;vb_single+=p==1;vb_multi+=p>1;vb_pages+=p;}else vb_invalid++;
 return ok;
}
static void vb_boundary(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[VM_COST] %u %llu %llu %llu %llu %llu %llu %llu %llu %llu\n",f,
 (unsigned long long)vb_calls,(unsigned long long)vb_single,(unsigned long long)vb_multi,(unsigned long long)vb_pages,(unsigned long long)vb_invalid,
 (unsigned long long)vb_n[0],(unsigned long long)vb_time[0],(unsigned long long)vb_n[1],(unsigned long long)vb_time[1]);
 if(!f||f==30){vb_rng=53951u+f;vb_calls=vb_single=vb_multi=vb_pages=vb_invalid=vb_n[0]=vb_n[1]=vb_time[0]=vb_time[1]=0;}
 vb_on=f<120;
}
