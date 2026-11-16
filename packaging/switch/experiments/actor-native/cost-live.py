"""Compare main-thread CPU spent applying one completed result vs original
actor execution, charging guest IRQs/fibers separately. Excludes the worker
and snapshot, so measures only whether publication could ever be worthwhile."""
from pathlib import Path
import subprocess as sp,sys
here=Path(__file__).resolve().parent
s=sp.check_output([sys.executable,here/'compact-live.py'],text=True)
s=s.replace('static unsigned replaced;', '''static unsigned replaced;static uint64_t cost_start,cost_charged;static int cost_on,cost_mode;
static uint64_t thread_now(void){struct timespec ts;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&ts);return (uint64_t)ts.tv_sec*1000000000+ts.tv_nsec;}
static void cost_begin(int mode){cost_mode=mode;cost_charged=0;cost_on=1;cost_start=thread_now();}
static void cost_end(void){if(cost_on)cost_charged+=thread_now()-cost_start;cost_on=0;
 fprintf(stderr,"[PUBLICATION_COST] frame=%u actor=%u replay=%d ns=%llu\\n",frame,id,cost_mode,(unsigned long long)cost_charged);cost_mode=-1;}
''')
a=s.index('static unsigned replaced;');b=s.index('int actor_replay(void)',a);decl=s[a:b];s=s[:a]+'static unsigned replaced;\n'+s[b:];decl=decl[decl.index('static uint64_t cost_start'):];i=s.index('void dep_key(unsigned k)');s=s[:i]+decl.replace('static int cost_on,cost_mode;','static int cost_on,cost_mode=-1;')+s[i:]
s=s.replace('void dep_key(unsigned k){','void dep_key(unsigned k){if(cost_on){cost_charged+=thread_now()-cost_start;cost_on=0;}')
s=s.replace('if(scope&&active&&stage){counting=1;', 'if(cost_mode>=0&&active&&stage){cost_on=1;cost_start=thread_now();}if(scope&&active&&stage){counting=1;')
s=s.replace(' if(!active||!stage||!scope)return 0;', ''' if(!active||!stage||!scope)return 0;
 static unsigned seq[64];if(!(seq[id]++&1)){if(pthread_join(worker,NULL))abort();scope=0;counting=0;cost_begin(0);return 0;}
''')
s=s.replace(' if(admit){',' cost_begin(1);\n if(admit){')
s=s.replace('  fprintf(stderr,"[COMPACT_LIVE]', '  cost_end();fprintf(stderr,"[COMPACT_LIVE]')
s=s.replace('void actor_end(void){','void actor_end(void){if(active&&stage&&cost_mode>=0)cost_end();')
print('#include <time.h>\n'+s)
