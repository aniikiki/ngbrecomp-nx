"""A/B all DMA parser code with aggressive inlining. Both versions share the
actual device registers, queue, IRQ state and vblank clock; dispatch once per PUT."""
from pathlib import Path
import sys,re
here=Path(__file__).resolve().parent;perf=here.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
p=NativeProbe('dma-island');p.driver((perf/'trial.inc').read_text())
s=(RUNTIME/'nv2a_boot.c').read_text()
a=s.index('static void *dma_commands(');b=s.index('/* Materialize GPU writes',a);body=s[a:b]
names=re.findall(r'^static (?:void \*|void |uint32_t |unsigned |int )(\w+)\(',body,re.M)
assert 'execute_dma' in names and 'dma_commands' in names
renamed=re.sub(r'\b('+'|'.join(names)+r')\b',lambda m:'opt_'+m[1],body)
new=body.replace('static void execute_dma(', 'static __attribute__((noinline)) void original_execute_dma(')
s=s[:a]+new+'\n#pragma GCC push_options\n#pragma GCC optimize ("O3")\n'+renamed.replace('static void opt_execute_dma(', 'static __attribute__((noinline)) void opt_execute_dma(')+'\n#pragma GCC pop_options\nextern unsigned trial_variant;static unsigned long long optimized_puts;unsigned long long dma_count(void){return optimized_puts;}\nstatic void execute_dma(uint32_t put){if(trial_variant){++optimized_puts;opt_execute_dma(put);}else original_execute_dma(put);}\n'+s[b:]
o=p.compile('nv2a_boot.c',s,['-fno-strict-aliasing']);p.link[p.link.index(next(i for i in p.link if i.endswith('/nv2a_boot.c.o')))]=o
p.link.insert(1,'-Wl,--strip-debug');s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;'
p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);extern unsigned long long dma_count(void);if(!(scene_flips%120))fprintf(stderr,"[DMA_OPT] %u %llu\\n",scene_flips,dma_count());ngb_trial_flip(scene_flips,draws);'));p.finish()
