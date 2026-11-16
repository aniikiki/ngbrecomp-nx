/* Host-only workload perturbation, never use these clocks as Switch timings. */
extern void __real_ngb_poll_due(uint64_t);
static _Thread_local unsigned cadence_on,cadence_scale;
static _Thread_local uint64_t cadence_cpu,cadence_wall,cadence_calls,cadence_sleeps;
static uint64_t cadence_read(clockid_t c){
 struct timespec t;if(clock_gettime(c,&t))abort();
 return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;
}
void __wrap_ngb_poll_due(uint64_t t){
 if(cadence_on && (t&4095u)==0){
  ++cadence_calls;
  if(cadence_scale){
   uint64_t w=cadence_read(CLOCK_MONOTONIC),c=cadence_read(CLOCK_THREAD_CPUTIME_ID);
   uint64_t aim=cadence_wall+cadence_scale*(c-cadence_cpu);
   if(aim>w){struct timespec ts={(time_t)(aim/1000000000),(long)(aim%1000000000)};
    int rc;do{rc=clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&ts,NULL);}while(rc==EINTR);
    if(rc)abort();
    ++cadence_sleeps;}
  }
 }
 __real_ngb_poll_due(t);
}
static void cadence_boundary(unsigned f){
 if(f>=31 && f<=120)fprintf(stderr,"[DRAW_CADENCE] %u %llu %llu\n",f,
  (unsigned long long)cadence_calls,(unsigned long long)cadence_sleeps);
 cadence_on=f>=30 && f<120;cadence_scale=getenv("NGB_DRAW_CADENCE")?6:0;
 cadence_calls=cadence_sleeps=0;
 if(cadence_on && cadence_scale){cadence_wall=cadence_read(CLOCK_MONOTONIC);cadence_cpu=cadence_read(CLOCK_THREAD_CPUTIME_ID);}
}
