/* Linux/ARM64 diagnostic: the guest runs on several cooperative stacks.
 * Read the interrupted stack through /proc/self/mem: a short read stops
 * the unwind without dereferencing an invalid or unmapped frame pointer. */
#include <fcntl.h>
#include <signal.h>
#include <sys/syscall.h>
#include <ucontext.h>
#include <unistd.h>
extern char __executable_start[];
static struct { uintptr_t pc[48]; unsigned count; } arm_samples[4096];
static sig_atomic_t volatile arm_used;
static int arm_mem;
static timer_t arm_timer;
static void arm_sample_signal(int sig, siginfo_t *info, void *raw)
{
    (void)sig; (void)info;
    int saved_errno=errno;
    unsigned i=arm_used;
    if(i<sizeof(arm_samples)/sizeof(*arm_samples)){
        const mcontext_t *ctx=&((ucontext_t*)raw)->uc_mcontext;
        uintptr_t sp=ctx->sp, fp=ctx->regs[29], copy[1024];
        unsigned n=0;
        arm_samples[i].pc[n++]=ctx->pc;
        ssize_t bytes=pread(arm_mem,copy,sizeof(copy),sp);
        while(bytes>=16 && fp>=sp && !(fp&15) && !(sp&7) &&
              fp-sp<=(size_t)bytes-16 && n<48){
            size_t at=(fp-sp)/sizeof(uintptr_t);
            uintptr_t parent=copy[at],ret=copy[at+1];
            if(ret<4 || (ret&3))break;
            arm_samples[i].pc[n++]=ret-4;
            if(parent<=fp)break;
            fp=parent;
        }
        arm_samples[i].count=n;
        arm_used=i+1;
    }
    errno=saved_errno;
}
static void arm_stack_window(unsigned flip)
{
    if(flip!=1680 && flip!=1920)return;
    struct itimerspec it={0};
    if(flip==1680){
        arm_mem=open("/proc/self/mem",O_RDONLY|O_CLOEXEC);
        struct sigaction sa={0};sa.sa_flags=SA_SIGINFO|SA_RESTART;sa.sa_sigaction=arm_sample_signal;
        sigemptyset(&sa.sa_mask);
        if(arm_mem<0 || sigaction(SIGPROF,&sa,NULL))abort();
        struct sigevent se={0};se.sigev_notify=SIGEV_THREAD_ID;se.sigev_signo=SIGPROF;
        se._sigev_un._tid=syscall(SYS_gettid);
        if(timer_create(CLOCK_THREAD_CPUTIME_ID,&se,&arm_timer))abort();
        it.it_value.tv_nsec=it.it_interval.tv_nsec=911231;
    }
    if(timer_settime(arm_timer,0,&it,NULL))abort();
    if(flip==1920){
        if(timer_delete(arm_timer))abort();
        close(arm_mem);
        for(int i=0;i<arm_used;i++){
            fprintf(stderr,"[ARMCHAIN]");
            for(unsigned k=0;k<arm_samples[i].count;k++)
                fprintf(stderr," %llx",(unsigned long long)(arm_samples[i].pc[k]-(uintptr_t)__executable_start));
            fputc('\n',stderr);
        }
    }
}
