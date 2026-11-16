extern double ngb_dev_sin(double),ngb_dev_cos(double);
static _Thread_local struct {unsigned on,rng,n[2],s[2],e[2];uint64_t t[2],b[2];} trig;
static uint64_t trig_now(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
static double trig_call(double x,unsigned op){
 unsigned sel=99;
 if(trig.on){trig.n[op]++;trig.rng=trig.rng*1664525u+1013904223u;sel=trig.rng>>27;}
 if(sel==1){uint64_t a=trig_now();__asm__ volatile("" ::: "memory");uint64_t b=trig_now();trig.e[op]++;trig.b[op]+=b-a;}
 if(sel==0){uint64_t a=trig_now();double y=op?ngb_dev_cos(x):ngb_dev_sin(x);__asm__ volatile("" : "+w"(y) :: "memory");uint64_t b=trig_now();trig.s[op]++;trig.t[op]+=b-a;return y;}
 return op?ngb_dev_cos(x):ngb_dev_sin(x);
}
double __wrap_sin(double x){return trig_call(x,0);}
double __wrap_cos(double x){return trig_call(x,1);}
static void trig_boundary(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<2;i++)fprintf(stderr,"[TARGET_TRIG] end=%u cos=%u calls=%u samples=%u empty=%u ns=%llu empty_ns=%llu\n",f,i,trig.n[i],trig.s[i],trig.e[i],(unsigned long long)trig.t[i],(unsigned long long)trig.b[i]);
 if(!f||f==30){memset(&trig,0,sizeof trig);trig.on=1;trig.rng=1234;}else if(f==120)trig.on=0;
}
