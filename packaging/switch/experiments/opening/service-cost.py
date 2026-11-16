"""Only re-scan timers when one may be due, including reentrant callbacks;
walk the same worker ring without a run-time division at each parked thread."""
from pathlib import Path
def timers(source):
 k='void ngb_timers_reset(void) {'
 source=source.replace(k,'static uint64_t earliest;\n'+k+' earliest=UINT64_MAX;')
 k='    timers[i].armed = 1;'
 source=source.replace(k,k+'\n    if(timers[i].due<earliest) earliest=timers[i].due;')
 k='    for (int i = 0; i < 32; ++i) {'
 assert source.count(k)==1
 source=source.replace(k,'    if(now < earliest) return;\n'+k)
 k='        fire(timers[i].address, timers[i].dpc, period != 0);\n    }'
 assert source.count(k)==1
 return source.replace(k,k+'\n    earliest=UINT64_MAX;\n    for(int i=0;i<32;i++) if(timers[i].armed && timers[i].due<earliest) earliest=timers[i].due;')
def workers(s):
 k='    for (unsigned n = 1; n < thread_count; ++n) {\n        unsigned i = (running_worker + n) % thread_count;'
 assert s.count(k)==1
 return s.replace(k,'    unsigned i=running_worker;\n    for (unsigned n = 1; n < thread_count; ++n) {\n        if (++i == thread_count) i=0;')
if __name__=='__main__':
 import tempfile,subprocess
 rt=Path(__file__).resolve().parents[2]/'runtime'
 with tempfile.TemporaryDirectory() as tmp:
  f=Path(tmp)/'timers.c';f.write_text(timers((rt/'timers.c').read_text()))
  exe=f.with_suffix('.exe')
  subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror','-I'+str(rt),f,rt/'timers_test.c','-o',exe],check=True)
  subprocess.run([exe],check=True)
