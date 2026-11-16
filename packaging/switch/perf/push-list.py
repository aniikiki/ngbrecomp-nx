"""Compare decoded index-list reuse with the original drawing path."""
from pathlib import Path
from native_probe import NativeProbe,ROOT,RUNTIME
here=Path(__file__).resolve().parent
import sys
trace='--trace' in sys.argv
span='--span' in sys.argv
p=NativeProbe('push-trace' if trace else ('push-span' if span else 'push-list'));p.driver((here/'trial.inc').read_text())
s=(ROOT/'src/d3d/hle.cpp').read_text()
s='extern "C"{extern unsigned trial_variant;unsigned push_seen,push_fast;extern unsigned char* ngb_fast_ram;extern unsigned short ngb_fast_page_bytes[];extern unsigned char ngb_target_pages[];}\n'+s
tag='void RunPushBuffer(uint32_t pb) {'
code=(here.parent/'experiments/push-list/fast.inc').read_text()
if span:code=(here.parent/'experiments/push-list/span.inc').read_text().replace('SpanPush(', 'CachedPush(')
s=s.replace(tag,'''static const uint8_t* PushSpan(uint32_t a,uint32_t n){
 for(unsigned page=a>>12;page<=(a+n-1)>>12;page++)if(ngb_fast_page_bytes[page]!=4096 || ngb_target_pages[page&32767])return nullptr;
 return ngb_fast_ram+(a&0x7fffffffu);}
'''+code+'\n'+tag)
if trace:
    tag='    if (size<20'
    s=s.replace(tag,'''    static unsigned printed;
    if(printed<120 && !(push_seen%101)){printed++;fprintf(stderr,"[PUSH_WORDS] data=%08x bytes=%u",data,size);
     for(unsigned k=0;k<size && k<192;){uint32_t h=R32(data+k);fprintf(stderr," %u:%08x",k,h);unsigned advance=4+4*((h>>18)&2047);k+=advance;}
     fprintf(stderr," last=%08x\\n",size>=4?R32(data+size-4):0);}
'''+tag)
tag='    std::vector<uint16_t> idx;';assert s.count(tag)==1
p.add('hle.cpp',s.replace(tag,'    if(trial_variant){push_seen++;if(CachedPush(data,size)){push_fast++;return;}}\n'+tag))
s=(RUNTIME/'scene/bridge.c').read_text();tag='    ++scene_flips;'
p.add('scene/bridge.c',s.replace(tag, tag+' extern unsigned push_seen,push_fast;extern void ngb_trial_flip(unsigned,unsigned);if(!(scene_flips%120))fprintf(stderr,"[PUSH] %u %u %u\\n",scene_flips,push_seen,push_fast);ngb_trial_flip(scene_flips,draws);'));p.finish()
