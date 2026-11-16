static _Thread_local unsigned sel_on,sel_rng;
static _Thread_local unsigned long long sel_calls,sel_n[2],sel_ns[2];
static unsigned long long sel_tick(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return (unsigned long long)t.tv_sec*1000000000+t.tv_nsec;}
unsigned long long select_cost_enter(void){
 if(!sel_on)return 0;
 sel_calls++;sel_rng=sel_rng*1664525u+1013904223u;
 unsigned r=sel_rng>>28;
 if(r==1){unsigned long long t=sel_tick();sel_ns[1]+=sel_tick()-t;sel_n[1]++;}
 return r==0?sel_tick():0;
}
void select_cost_leave(unsigned long long t){if(t){sel_ns[0]+=sel_tick()-t;sel_n[0]++;}}
static void sel_boundary(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[SELECT_COST] %u calls=%llu samples=%llu ns=%llu empty_samples=%llu empty_ns=%llu\n",f,sel_calls,sel_n[0],sel_ns[0],sel_n[1],sel_ns[1]);
 if(!f||f==30){sel_rng=9531+f;sel_calls=sel_n[0]=sel_n[1]=sel_ns[0]=sel_ns[1]=0;}
 sel_on=f<120;
}
