"""Classify a complete header by indexed method instead of running seven range
comparisons on every packet. Construct an exhaustive table from the original
predicate; injected only in offline game. Keep the full parser for controls."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
p=NativeProbe('fifo-table');p.driver((perf/'trial.inc').read_text())
s=(RUNTIME/'nv2a_boot.c').read_text()
tag='static unsigned state_packet_size(uint32_t header)'
s=s.replace(tag,'''extern unsigned trial_variant;
static unsigned short method_run[2048];static unsigned valid_table;static uint64_t used_table;
static unsigned table_size(uint32_t header){
    if(!valid_table){for(unsigned i=0;i<2048;i++){unsigned m=i*4;
        method_run[i]=m==NV097_SET_TRANSFORM_CONSTANT_LOAD?1:direct_state_words(m);}
        valid_table=1;}
    unsigned count=header>>18;
    return !(header & ~(NV_PFIFO_CACHE1_DMA_STATE_METHOD | NV_PFIFO_CACHE1_DMA_STATE_METHOD_COUNT))
        && count && count<=method_run[(header>>2)&2047] ? count+1:0;
}
unsigned long long fifo_classified(void){return used_table;}
'''+tag)
a=s.index('    unsigned used = 0, packets = 0;',s.index('static unsigned retire_state_packets'))
s=s[:a]+s[a:].replace('    unsigned used = 0, packets = 0;', '''    if(trial_variant){
        unsigned used=0,packets=0,last=0;
        uint32_t header=first;
        do{
            last=((header&NV_PFIFO_CACHE1_DMA_STATE_METHOD)+4*(words-1))&NV_PFIFO_CACHE1_DMA_STATE_METHOD;
            used+=words;packets++;
            if(used==available)break;
            memcpy(&header,mapped+off+used*4,4);
            words=table_size(header);
        }while(words && words<=available-used);
        *state=last;packet_count+=packets;param_count+=used-packets;
        direct_batched_words+=used-packets;used_table+=packets;return used*4;
    }
    unsigned used = 0, packets = 0;''',1)
o=p.compile('nv2a_boot.c',s);p.link[p.link.index(next(i for i in p.link if i.endswith('/nv2a_boot.c.o')))]=o
p.link.insert(1,'-Wl,--strip-debug')
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);extern unsigned long long fifo_classified(void);if(!(scene_flips%120))fprintf(stderr,"[CLASSIFIED] %u %llu\\n",scene_flips,fifo_classified());ngb_trial_flip(scene_flips,draws);'));p.finish()
