"""Measure complete live actor wave on adjacent frames: snapshot, submitting
two workers, wait, callback execution and result publication all included.
No heavy reference instrumentation in either variant. This intentionally
tests deferred visibility, not yet suitable for arbitrary live inputs."""
from pathlib import Path
import shlex,sys,subprocess as sp,re
here=Path(__file__).resolve().parent;root=Path('/work');base=root/'build/switch-runtime';d=base/'core-perf/actor-whole-frame';d.mkdir(exist_ok=True)
sys.path.insert(0,str(here.parents[1]/'perf'));from native_probe import NativeProbe,RUNTIME
mode=sys.argv[1]
if mode=='cross':
 n='recomp_0010.c';s=(base/'gen'/n).read_text()
 tag='loc_00147ECD: ;';end='loc_00147EE6: ;';assert s.count(tag)==s.count(end)==1
 s='void actor_begin(unsigned,unsigned,unsigned);int actor_replay(void);void actor_end(void);\n'+s.replace(tag,tag+' actor_begin(2,edi,esp);if(actor_replay())goto loc_00147EE6;').replace(end,end+' actor_end();')
 src=d/n;src.write_text(s);c=next(shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=base/'switch',text=True).splitlines() if x.endswith('/'+n));o=str(d/'loop.o');c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(src);c.insert(-1,'-g0');sp.run(c,cwd=base/'switch',check=True);sys.exit(0)
import json
persistent='--persistent' in sys.argv
adaptive='--adaptive' in sys.argv
timed='--wall' in sys.argv
bulk='--bulk' in sys.argv
cache='--page-cache' in sys.argv
p=NativeProbe(('actor-persistent' if persistent else 'actor-whole-frame')+('-wall' if timed else '')+('-adaptive' if adaptive else '')+('-bulk' if bulk else '')+('-pages' if cache else ''));p.link=json.loads((p.core/'exact-link.json').read_text());l=p.link
l[l.index(next(v for v in l if v.endswith('/recomp_0010.o')))]=str(d/'loop.o')
s=sp.check_output([sys.executable,here/'joined-wave.py'],text=True)
s=s[:s.index('static inline void observe(')]
s=s.replace('extern unsigned dep_task,','static unsigned dep_task;extern unsigned ').replace('unsigned trial_variant=1,actor_fork_child;', 'extern unsigned trial_variant;unsigned actor_fork_child;')
# Initialize once on actual guest RAM. Without the TSAN hooks active/id only
# changes in the sorted loop; other guest tasks must not reenter it.
s=s.replace('dep_key(k);}', '(void)k;}')
s=s.replace('frame>=1802&&waves<6','frame>=1801&&(waves==0||trial_variant)')
s=s.replace('frame=f>=1801&&f<=1820?f:0;', 'frame=f>=1681&&f<=1920?f:0;')
s=s.replace('if(count<2||count>32||(s&4095)>4060)abort();','if(count!=11||(s&4095)>4060)return;')
s=s.replace('if(!on||!active||!phase||id==0||waves<=1)return 0;', 'if(!on||!active||!phase||id==0||waves<=1)return 0;')
s=s.replace('if(!frame)return;unsigned i=', 'if(!frame&&!on)return;unsigned i=')
s=s.replace('struct job*j=jobs+pos;if(j->err)return 0;', 'for(unsigned u=1;u<count;u++)if(jobs[u].err)return 0;struct job*j=jobs+pos;')
# Speed measurement: no per-job logs, reference recomputation, or page delta
# comparisons unless training. Disabled frame still executes original calls.
tag='struct job*j=jobs+pos;unsigned diff=0';a=s.index(tag);b=s.index('if(pos+1==count){on=0',a)
s=s[:a]+s[b:]
s=re.sub(r' fprintf\(stderr,"\[JOINED_WAVE\].*?;\n',' ++retirements;\n',s)
s=s.replace('void dep_flip(unsigned f,unsigned k){','unsigned whole_adopted(void){return retirements;}\nvoid dep_flip(unsigned f,unsigned k){')
# All runs use the actual original kernel poll and callback routine.
rt=(p.core/'exact-runtime.inc').read_text()
t=(root/'packaging/switch/perf/pair.py').read_text();a=t.index('int actor_service_due(void)');b=t.index('void actor_commit_events(',a)
rt+='\n'+t[a:b]+'\nunsigned fork_regs(void*r,uint64_t*e){memcpy(r,&g_regs,sizeof g_regs);*e=entries;return sizeof g_regs;}\n'
rt=rt.replace('ngb_vm_init(ram);','ngb_vm_init(ram);extern void dep_bind(void*);dep_bind(ram);')
if bulk:
 rt+='''
void actor_retire_run(const unsigned char *trace,unsigned limit,unsigned bytes){
 for(unsigned t=1;t<=limit;){
   unsigned mask=ngb_poll_mask;
   unsigned n=ngb_pending_dpcs?0:mask-((unsigned)ngb_guest_polls&mask);
   if(n>limit-t+1)n=limit-t+1;
   for(unsigned e=t;e<t+n;e++){
     unsigned pc;memcpy(&pc,trace+320*e+bytes,4);
     if(pc>>31)recent[entries++%32]=current_va=pc&0x7fffffffu;
   }
   ngb_guest_polls+=n;t+=n;
   if(t<=limit){actor_stress_event((unsigned char*)trace+320*t,bytes);++t;}
 }
}
'''
 a=s.index(' for(unsigned t=1;t<=j->polls;t++)');b=s.index(' /* Merge only',a)
 s=s[:a]+' extern void actor_retire_run(const unsigned char*,unsigned,unsigned);actor_retire_run(j->trace,j->polls,nr);\n'+s[b:]
(p.out/'whole-runtime.inc').write_text(rt)
driver=(p.core/'exact-test.c').read_text().replace('exact-runtime.inc','whole-runtime.inc');tag='void __real_ngb_kernel_log'
trial=(root/'packaging/switch/perf/trial.inc').read_text()
if timed:
 anchor='    before = now;'
 trial=trial.replace(anchor,'''    static uint64_t last_wall;
    if(clock_gettime(CLOCK_MONOTONIC,&t))abort();
    uint64_t real=(uint64_t)t.tv_sec*1000000000u+t.tv_nsec;
    if(frame!=start)fprintf(stderr,"[FRAME_WALL] %u %u %llu\\n",frame,trial_variant,(unsigned long long)(real-last_wall));
    last_wall=real;
'''+anchor)
driver=driver.replace(tag,trial+tag)
l[l.index(str(p.core/'exact-runtime_test.c.o'))]=p.compile('runtime_test.c',driver,['-include',str(RUNTIME/'switch_guest_regs.h'),'-I'+str(p.core),'-I'+str(RUNTIME)])
if persistent:
 from persistent import transform
 s=transform(s)
if adaptive:
 from adaptive import transform
 s=transform(s)
if timed:
 # Bracket both implementations identically. A flip can occur inside a
 # callback: label each loop by its entry frame, not by the next flip.
 s=s.replace('void actor_begin(unsigned ph', """static uint64_t loop_start;
 static unsigned loop_left,loop_frame,loop_variant,loop_adopt;
 void actor_begin(unsigned ph""")
 tag='prior[ph-1][i]=dep_task;'
 s=s.replace(tag,"""if(i==0 && frame>=1800){uint64_t dummy;union regs state;fork_regs(state.bytes,&dummy);
 loop_left=state.r[4];loop_frame=frame;loop_variant=trial_variant;loop_adopt=retirements;loop_start=nsec();}
 """+tag)
 # The counter is defined after actor_begin in the generated file.
 s=s.replace('static uint64_t loop_start;', 'static unsigned retirements;static uint64_t loop_start;')
 s=s.replace('dep_task=prior[phase][id];', """if(loop_left && !--loop_left)fprintf(stderr,"[WAVE_WALL] %u %u %llu %u\\n",
 loop_frame,loop_variant,(unsigned long long)(nsec()-loop_start),retirements-loop_adopt);
 dep_task=prior[phase][id];""")
f=p.out/'runner.c';f.write_text(s);o=p.out/'runner.o';sp.run(['cc','-O2','-c',f,'-o',o],check=True)
l[1:1]=[str(o),str(base/'opt050'/('actor-pages' if cache else 'actor-wave-state')/'footprint.o'),'-Wl,--strip-debug']
src=(RUNTIME/'scene/bridge.c').read_text();tag='    ++scene_flips;';p.add('scene/bridge.c',src.replace(tag,tag+' extern void ngb_trial_flip(unsigned,unsigned),dep_flip(unsigned,unsigned);extern unsigned whole_adopted(void);ngb_trial_flip(scene_flips,draws);dep_flip(scene_flips,0);if(!(scene_flips%120))fprintf(stderr,"[WHOLE_WAVE] %u %u\\n",scene_flips,whole_adopted());'));p.finish()
