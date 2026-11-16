#include <sys/syscall.h>
#include <unistd.h>
#include <signal.h>
#include <ucontext.h>
#include <dlfcn.h>
#include <time.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static _Thread_local volatile uintptr_t active_clock,clock_parent,elapsed_parent;
int __real_clock_gettime(clockid_t,struct timespec*);
__attribute__((noinline)) int __wrap_clock_gettime(clockid_t id,struct timespec *ts){
 uintptr_t old=active_clock;active_clock=(uintptr_t)__builtin_return_address(0);
 int result=__real_clock_gettime(id,ts);active_clock=old;return result;
}
static volatile sig_atomic_t pc_used,pc_lost,pc_frame;
static struct {uintptr_t pc,lr,clock,parent,outer; unsigned frame;} pc_rows[8192];
static void pc_sample(int s,siginfo_t* si,void* ctx){
 (void)s;
 if(pc_used<8192){pc_rows[pc_used].pc=((ucontext_t*)ctx)->uc_mcontext.pc;
 pc_rows[pc_used].parent=clock_parent;pc_rows[pc_used].outer=elapsed_parent;pc_rows[pc_used].clock=active_clock;pc_rows[pc_used].lr=((ucontext_t*)ctx)->uc_mcontext.regs[30];pc_rows[pc_used].frame=pc_frame;pc_used++;}
 else pc_lost++;
 pc_lost+=si->si_overrun;
}
void phase_flip(unsigned f){
 static timer_t tm;static sigset_t mask;static struct itimerspec spec;
 if(!f){
 struct sigaction sa={0};sa.sa_sigaction=pc_sample;sa.sa_flags=SA_RESTART|SA_SIGINFO;
 sigemptyset(&mask);sigaddset(&mask,SIGRTMIN+6);
 if(sigaction(SIGRTMIN+6,&sa,0))abort();
 struct sigevent se={0};se.sigev_notify=SIGEV_THREAD_ID;se.sigev_signo=SIGRTMIN+6;se._sigev_un._tid=syscall(SYS_gettid);
 if(timer_create(CLOCK_THREAD_CPUTIME_ID,&se,&tm))abort();
 pc_frame=1;spec.it_value.tv_nsec=spec.it_interval.tv_nsec=getenv("NGB_PC_REPEAT")?991027:887123;
 if(timer_settime(tm,0,&spec,0))abort();
 }else if(f<120)pc_frame=f+1;
 else if(f==120){
 if(pthread_sigmask(SIG_BLOCK,&mask,0))abort();
 struct itimerspec stop={0};if(timer_settime(tm,0,&stop,0))abort();
 for(int j=0;j<pc_used;j++)fprintf(stderr,"[FRAME_PC] %u %lx\n",pc_rows[j].frame,(unsigned long)pc_rows[j].pc);
 for(int j=0;j<pc_used;j++){Dl_info info;
 if(dladdr((void*)pc_rows[j].pc,&info)&&info.dli_fname)
 fprintf(stderr,"[FRAME_MODULE] %u %lx %lx %s %s\n",pc_rows[j].frame,(unsigned long)pc_rows[j].pc,(unsigned long)(pc_rows[j].pc-(uintptr_t)info.dli_fbase),info.dli_fname,info.dli_sname?info.dli_sname:"?");}
 for(int j=0;j<pc_used;j++)fprintf(stderr,"[FRAME_LR] %u %lx %lx\n",pc_rows[j].frame,(unsigned long)pc_rows[j].pc,(unsigned long)pc_rows[j].lr);
 for(int j=0;j<pc_used;j++)if(pc_rows[j].clock)fprintf(stderr,"[CLOCK_ORIGIN] %u %lx %lx\n",pc_rows[j].frame,(unsigned long)pc_rows[j].pc,(unsigned long)pc_rows[j].clock);
 for(int j=0;j<pc_used;j++)if(pc_rows[j].parent)fprintf(stderr,"[CLOCK_PARENT] %u %lx %lx\n",pc_rows[j].frame,(unsigned long)pc_rows[j].pc,(unsigned long)(pc_rows[j].outer?pc_rows[j].outer:pc_rows[j].parent));
 fprintf(stderr,"[FRAME_PC_COUNT] %d %d\n",pc_used,pc_lost);
 if(timer_delete(tm))abort();
 if(pthread_sigmask(SIG_UNBLOCK,&mask,0))abort();
 }
}
