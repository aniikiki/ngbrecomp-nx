"""Measure how often the full NV2A timer conversion and alarm actually run."""
counters=r"""
unsigned cc_active,cc_ticks,cc_div,cc_equal,cc_alarm,cc_expired,cc_vblank,cc_changed;
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[CLOCK_CENSUS] %u %u %u %u %u %u %u %u\n",f,cc_ticks,cc_div,cc_equal,cc_alarm,cc_expired,cc_vblank,cc_changed);
 if(!f||f==30){cc_ticks=cc_div=cc_equal=cc_alarm=cc_expired=cc_vblank=cc_changed=0;}
 cc_active=f<120;
}
"""
def transform(s):
 s='extern unsigned cc_active,cc_ticks,cc_div,cc_equal,cc_alarm,cc_expired,cc_vblank,cc_changed;\n'+s
 for k,code in [
 ('    if (!(engines & ENGINE_TIMER) || !timer_num) return timer_base;', 'if(cc_active)cc_ticks++;'),
 ('    const uint64_t core_hz = NV2A_CRYSTAL_FREQ * 14ull;', 'if(cc_active){++cc_div;cc_equal+=timer_num==timer_den;}'),
 ('    if (!(engines & ENGINE_TIMER) || !(timer_irq & NV_PTIMER_INTR_0_ALARM)) return;', 'if(cc_active)cc_alarm++;'),
 ('        alarm_tick = next_alarm(ticks);','if(cc_active)cc_expired++;'),
 ('    uint64_t current = ngb_elapsed_ns() / 16666667u;', 'if(cc_active)cc_vblank++;'),
 ('        crtc_status |= NV_PCRTC_INTR_0_VBLANK;','if(cc_active)cc_changed++;')]:
  assert s.count(k)==1,k
  s=s.replace(k,'    '+code+'\n'+k)
 return s
