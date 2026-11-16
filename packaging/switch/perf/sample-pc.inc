/* Linux AArch64 only. Profile the thread that runs the recompiled Xbox,
 * excluding renderer CPU and blocked time; no unwinding in the handler. */
#include <signal.h>
#include <sys/syscall.h>
#include <ucontext.h>
extern char __executable_start[];
static uintptr_t sample_pcs[16384];
static volatile sig_atomic_t sample_count;
static timer_t sample_timer;
static void sample_signal(int sig, siginfo_t *info, void *state)
{
    (void)sig; (void)info;
    sig_atomic_t n=sample_count;
    if ((unsigned)n<sizeof(sample_pcs)/sizeof(sample_pcs[0])) {
        sample_pcs[n]=((ucontext_t*)state)->uc_mcontext.pc;
        sample_count=n+1;
    }
}
static void sample_window(unsigned flip)
{
    if (flip!=1680 && flip!=1920) return;
    struct itimerspec arm={0};
    if (flip==1680) {
        struct sigaction sa={0}; sa.sa_flags=SA_SIGINFO|SA_RESTART;
        sa.sa_sigaction=sample_signal; sigemptyset(&sa.sa_mask);
        if(sigaction(SIGPROF,&sa,NULL)) abort();
        struct sigevent sev={0}; sev.sigev_notify=SIGEV_THREAD_ID;
        sev._sigev_un._tid=syscall(SYS_gettid); sev.sigev_signo=SIGPROF;
        if(timer_create(CLOCK_THREAD_CPUTIME_ID,&sev,&sample_timer)) abort();
        arm.it_value.tv_nsec=arm.it_interval.tv_nsec=907003;
    }
    if(timer_settime(sample_timer,0,&arm,NULL)) abort();
    if (flip==1920) {
        if(timer_delete(sample_timer)) abort();
        fprintf(stderr,"[ARMBASE] %llx\n",(unsigned long long)(uintptr_t)__executable_start);
        FILE *maps=fopen("/proc/self/maps","r");
        if(!maps) abort();
        char row[2048];
        while(fgets(row,sizeof(row),maps)) fprintf(stderr,"[ARMMAP] %s",row);
        fclose(maps);
        for(int i=0;i<sample_count;i++)
            fprintf(stderr,"[ARMPC] %llx\n",(unsigned long long)(sample_pcs[i]-(uintptr_t)__executable_start));
    }
}
