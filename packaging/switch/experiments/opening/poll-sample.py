"""CPU-clock sampling of original poll work. No hot-path clock reads.
Deliver only to the cooperative guest's Linux thread; switch scope with fibers."""
def install(p,rt,src):
 w=(rt/'workers.inc').read_text()
 for t in ('worker','fiber'):
    k='static struct '+t+' {';assert w.count(k)==1;w=w.replace(k,k+'\n unsigned poll_saved;')
 for t in ('dest','next'):
    k=f'ngb_ctx_switch(&old->sp, {t}->sp);';assert w.count(k)==1;w=w.replace(k,f'old->poll_saved=poll_scope;poll_scope={t}->poll_saved;'+k)
 (p.out/'poll-workers.inc').write_text(w)
 s=(p.out/'host-runtime.inc').read_text()
 s=s.replace('#include "workers.inc"','#include "poll-workers.inc"')
 a=s.index('void ngb_poll_due(uint64_t ticket)\n{');b=s.index('static void poll_runtime',a)
 body=s[a:b]
 for i,k in enumerate(['poll_callbacks();','ngb_audio_poll();','yield_worker();','ngb_timers_poll(now_ns() / 100, fire_timer);'],1):
    assert body.count(k)==1,k;body=body.replace(k,f'PS_DO({i},{k})')
 s=s[:a]+body+s[b:]
 k='    fn();\n    if (g_esp !=';assert s.count(k)==1;s=s.replace(k,'    PS_DO(5,fn();)\n    if (g_esp !=')
 (p.out/'poll-runtime.inc').write_text(r'''
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
#include <signal.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <time.h>
static volatile sig_atomic_t poll_scope,poll_bins[6],poll_lost;
#define PS_DO(i,stmt) do{sig_atomic_t prev=poll_scope;poll_scope=i;stmt poll_scope=prev;}while(0);
static void ps_tick(int s,siginfo_t *si,void *unused){(void)s;(void)unused;poll_bins[poll_scope]++;poll_lost+=si->si_overrun;}
static void phase_flip(unsigned f){
 if(f!=0 && f!=30 && f!=120)return;
 static timer_t timer;static sigset_t mask;
 if(!f){struct sigaction sa={0};sa.sa_sigaction=ps_tick;sa.sa_flags=SA_SIGINFO|SA_RESTART;
 sigemptyset(&mask);sigaddset(&mask,SIGRTMIN+5);if(sigaction(SIGRTMIN+5,&sa,0))abort();
 struct sigevent se={0};se.sigev_notify=SIGEV_THREAD_ID;se.sigev_signo=SIGRTMIN+5;se._sigev_un._tid=syscall(SYS_gettid);
 if(timer_create(CLOCK_THREAD_CPUTIME_ID,&se,&timer))abort();}
 if(pthread_sigmask(SIG_BLOCK,&mask,0))abort();
 if(f){fprintf(stderr,"[POLL_SAMPLE] %u %d",f,poll_lost);for(int i=0;i<6;i++)fprintf(stderr," %d",poll_bins[i]);fputc(10,stderr);}
 memset((void*)poll_bins,0,sizeof poll_bins);poll_lost=0;
 struct itimerspec spec={0};if(f<120){spec.it_value.tv_nsec=spec.it_interval.tv_nsec=997003;}
 if(timer_settime(timer,0,&spec,0))abort();
 if(pthread_sigmask(SIG_UNBLOCK,&mask,0))abort();}
'''.replace('static void phase_flip','void phase_flip')+s)
 assert src.count('"host-runtime.inc"')==1
 return '#define _GNU_SOURCE 1\n'+src.replace('"host-runtime.inc"','"poll-runtime.inc"')
