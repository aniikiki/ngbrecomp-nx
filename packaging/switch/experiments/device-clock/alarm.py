"""Offline paired device timer: exact inverse deadline, original IRQ and ack."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('alarm-clock')
p.driver((ROOT/'packaging/switch/perf/trial.inc').read_text())
s=(RUNTIME/'nv2a_boot.c').read_text().replace('static void sample_alarm(void)','''extern unsigned trial_variant;
static uint64_t next_alarm_ns;
static unsigned long long visits,full,fast;
static void sample_alarm(void)''')
s=s.replace('uint64_t ticks = timer_ticks(ngb_elapsed_ns());','''uint64_t now=ngb_elapsed_ns();
    if(trial_variant && now<next_alarm_ns){++fast;return;}
    ++full;
    uint64_t ticks=timer_ticks(now);''',1)
a='        alarm_tick = next_alarm(ticks);\n    }'
assert s.count(a)==1
s=s.replace(a,a+'''
    // First nanosecond at which floor((now-epoch)*rate/divisor)
    // reaches (alarm_tick-base). Saturate if beyond uint64_t time.
    if(trial_variant){
        if(!timer_num || !timer_den){next_alarm_ns=ticks<alarm_tick?UINT64_MAX:0;return;}
        if(alarm_tick<=timer_base){next_alarm_ns=0;return;}
        __uint128_t rate=(__uint128_t)NV2A_CRYSTAL_FREQ*14*timer_den;
        __uint128_t duration=((__uint128_t)(alarm_tick-timer_base)*1000000000u*timer_num+rate-1)/rate;
        next_alarm_ns=duration>UINT64_MAX-timer_epoch?UINT64_MAX:timer_epoch+(uint64_t)duration;
    }else next_alarm_ns=0;''')
for tag in ['static void reset_timer(void)\n{','case TIMER_NUM: case TIMER_DEN: {','case TIMER_LOW: case TIMER_HIGH: {','case TIMER_ALARM:\n        alarm_low']:
 assert s.count(tag)==1
 if 'alarm_low' in tag:s=s.replace(tag,tag.replace('alarm_low','next_alarm_ns=0;alarm_low'))
 elif 'case' in tag:s=s.replace(tag+'\n        sample_alarm();',tag+'\n        sample_alarm();next_alarm_ns=0;')
 else:s=s.replace(tag,tag+'\n    next_alarm_ns=0;')
k='uint32_t ngb_nv2a_irq_pending(void)\n{';assert s.count(k)==1
s=s.replace(k,k+'\n    if(!(++visits%1000000))fprintf(stderr,"[ALARM] calls=%llu due_checks=%llu avoided=%llu\\n",visits,full,fast);')
s='#include <stdio.h>\n'+s
o=p.compile('nv2a_boot.c',s)
old=[i for i,v in enumerate(p.link) if v.endswith('/nv2a_boot.c.o')];assert len(old)<=1
if old:p.link[old[0]]=o
else:p.link.insert(1,o)
s=(RUNTIME/'scene/bridge.c').read_text().replace('    ++scene_flips;', '    ++scene_flips;extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);')
p.add('scene/bridge.c',s);p.finish()
