"""Measure title-side waits by origin on the calling thread; no render-thread clock reads."""
def transform(t):
 k='    void Wait(uint64_t id, bool hand_over = true) {';assert t.count(k)==1
 t=t.replace(k,k+'\n        unsigned phase=ngb_wait_phase; unsigned kind=hand_over?0:1;\n        if(phase) ++ngb_wait_calls[kind];')
 k='        ngb_direct_render_event(false, true);';assert t.count(k)==1
 t=t.replace(k,'        uint64_t wait_start=phase?ngb_wait_now():0;\n'+k)
 k='            ngb_direct_render_event(false, false);';assert t.count(k)==1
 t=t.replace(k,k+'\n            if(phase && phase==ngb_wait_phase){++ngb_wait_blocked[kind];ngb_wait_ns[kind]+=ngb_wait_now()-wait_start;}')
 return 'extern "C" {extern thread_local unsigned ngb_wait_phase,ngb_wait_calls[2],ngb_wait_blocked[2];extern thread_local unsigned long long ngb_wait_ns[2];unsigned long long ngb_wait_now(void);}\n'+t
counters=r"""
_Thread_local unsigned ngb_wait_phase,ngb_wait_calls[2],ngb_wait_blocked[2];
_Thread_local unsigned long long ngb_wait_ns[2];
unsigned long long ngb_wait_now(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();return t.tv_sec*1000000000ull+t.tv_nsec;}
void phase_flip(unsigned f){
 if(ngb_wait_phase && (f<=4||f==30||f==120)){
 for(unsigned k=0;k<2;k++)fprintf(stderr,"[WAIT_ORIGIN] %u %u %u %u %llu\n",f,k,ngb_wait_calls[k],ngb_wait_blocked[k],ngb_wait_ns[k]);
 }
 if(f<=4||f==30){memset(ngb_wait_calls,0,sizeof ngb_wait_calls);memset(ngb_wait_blocked,0,sizeof ngb_wait_blocked);memset(ngb_wait_ns,0,sizeof ngb_wait_ns);}
 ngb_wait_phase=f<120?f+1:0;
}
"""
