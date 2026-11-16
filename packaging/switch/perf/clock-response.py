"""Does slow simulated hardware time create extra work per drawn frame?
Only change the guest monotonic clock during the final heavy sequence.
The observer clocks and full renderer remain real in both experiments."""
from native_probe import NativeProbe,REGS,RUNTIME
p=NativeProbe('clock-response')
s=(REGS/'host-runtime.inc').read_text()
k='static uint64_t now_ns(void)\n{';assert s.count(k)==1
s=s.replace(k,'static uint64_t raw_ns(void)\n{')
k='static int startup_expired';assert s.count(k)==1
s=s.replace(k,'''
static uint64_t real_anchor,guest_anchor;
static double guest_ratio=1.;
static uint64_t now_ns(void) {
    uint64_t now=raw_ns();
    return real_anchor ? guest_anchor+(uint64_t)((now-real_anchor)*guest_ratio) : now;
}
void clock_response(unsigned f,unsigned draws) {
    static unsigned target,prevdraw;
    static uint64_t prevreal,prevguest,prevcpu,preventries,prevpoll;
    static double ema;
    if(f<1620 || f>1920)return;
    if(!target){target=atoi(getenv("NGB_CLOCK_MS"));if(target!=17 && target!=50)abort();}
    struct timespec ts;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&ts))abort();
    uint64_t cpu=(uint64_t)ts.tv_sec*1000000000+ts.tv_nsec;
    uint64_t now=raw_ns(),virt=real_anchor?guest_anchor+(uint64_t)((now-real_anchor)*guest_ratio):now;
    if(prevreal){
        double dt=now-prevreal;ema=ema?0.90*ema+0.10*dt:dt;
        if(f>1680)fprintf(stderr,"[RATE] %u %u %llu %llu %llu %u %llu %llu\\n",f,target,
            (unsigned long long)(now-prevreal),(unsigned long long)(virt-prevguest),(unsigned long long)(cpu-prevcpu),
            draws-prevdraw,(unsigned long long)(entries-preventries),(unsigned long long)(ngb_guest_polls-prevpoll));
        if(f>=1680){
            guest_anchor=virt;real_anchor=now;guest_ratio=target*1e6/ema;
            if(guest_ratio<.025)guest_ratio=.025;
            if(guest_ratio>8.)guest_ratio=8.;
        }
    }
    prevreal=now;prevguest=virt;prevcpu=cpu;prevdraw=draws;preventries=entries;prevpoll=ngb_guest_polls;
}
'''+k)
(p.out/'host-runtime.inc').write_text(s);p.driver('')
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';assert s.count(k)==1
p.add('scene/bridge.c',s.replace(k,k+' extern void clock_response(unsigned,unsigned);clock_response(scene_flips,draws);'))
p.finish()
