"""Retire complete HLE-consumed Kelvin packets including nonincrementing ones.
Preserve parser-visible state, DMA object lookup, draw counts, clear callback
arguments, semaphore/flip/IRQ and all partially consumed packets."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent;perf=here.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
fusion='--draws' in sys.argv
check='--check' in sys.argv
p=NativeProbe('fifo-retire'+('-draws' if fusion else '')+('-check' if check else ''));p.driver((perf/'trial.inc').read_text())
s='#include <stdlib.h>\n'+(RUNTIME/'nv2a_boot.c').read_text()
a=s.index('static unsigned retire_state_packets')
s=s[:a]+'''extern unsigned trial_variant;
static unsigned short plain_words[2048]; static int plain_ready;
static unsigned long long extra_packets;
static unsigned packet_plain(uint32_t m){
    // Object lookups take place before the HLE hook. Low methods include
    // notifications, flip control and stalls; never combine any of them.
    if(m<0x200u)return 0;
    switch(m){
    case NV097_SET_BEGIN_END: case NV097_CLEAR_SURFACE:
    case NV097_FLIP_INCREMENT_WRITE: case NV097_FLIP_STALL:
    case NV097_NO_OPERATION: case NV097_WAIT_FOR_IDLE:
    case NV097_SET_FLIP_READ: case NV097_SET_FLIP_WRITE: case NV097_SET_FLIP_MODULO:
    case NV097_SET_SEMAPHORE_OFFSET: case NV097_BACK_END_WRITE_SEMAPHORE_RELEASE:
    case NV097_SET_ZSTENCIL_CLEAR_VALUE: case NV097_SET_COLOR_CLEAR_VALUE:return 0;
    default:return 1;
    }
}
static unsigned broad_packet(uint32_t h){
    if(h & ~(NV_PFIFO_CACHE1_DMA_STATE_METHOD|NV_PFIFO_CACHE1_DMA_STATE_METHOD_COUNT|0x40000000u))return 0;
    if(!plain_ready){unsigned run=0;for(int i=2047;i>=0;--i){run=packet_plain(i*4)?run+1:0;plain_words[i]=run;}plain_ready=1;}
    unsigned n=(h&NV_PFIFO_CACHE1_DMA_STATE_METHOD_COUNT)>>18,run=plain_words[(h&NV_PFIFO_CACHE1_DMA_STATE_METHOD)/4];
    return n && run && ((h&0x40000000u)||n<=run)?n+1:0;
}
unsigned long long fifo_extra_packets(void){return extra_packets;}
'''+s[a:]
s=s.replace('unsigned words = state_packet_size(first);','int broad=trial_variant && ngb_scene_active;\n    unsigned words=broad?broad_packet(first):state_packet_size(first);')
a=s.index('        *state = ((header');b=s.index('        used += words;',a)
s=s[:a]+'''        if(broad && (header&0x40000000u)) *state=(header&NV_PFIFO_CACHE1_DMA_STATE_METHOD)|1u;
        else *state=((header&NV_PFIFO_CACHE1_DMA_STATE_METHOD)+4*(words-1))&NV_PFIFO_CACHE1_DMA_STATE_METHOD;
'''+s[b:]
s=s.replace('words = state_packet_size(header);','words = broad?broad_packet(header):state_packet_size(header);').replace('    packet_count += packets;', '    if(broad)extra_packets+=packets;\n    packet_count += packets;')
if fusion:
 s=s.replace('static unsigned short plain_words','extern void ngb_scene_count_ends(unsigned); static unsigned long long fused_ends;\nstatic unsigned short plain_words')
 # HLE consumes primitive commands; a zero BEGIN_END counts a completed draw.
 # Only accept exact single-word packets, and commit the count before any
 # subsequent control method, interrupt, context switch or end of page.
 tag='    unsigned n=(h&NV_PFIFO_CACHE1_DMA_STATE_METHOD_COUNT)>>18,run='
 s=s.replace(tag,'    if(h==((1u<<18)|NV097_SET_BEGIN_END))return 2;\n'+tag)
 tag='    do {\n        if(broad && (header&0x40000000u))'
 assert s.count(tag)==1
 s=s.replace(tag,"""    unsigned ends=0;
    do {
        if(broad && header==((1u<<18)|NV097_SET_BEGIN_END)){
          uint32_t val;memcpy(&val,mapped+off+(used+1u)*4u,4);ends+=val==0;
        }
        if(broad && (header&0x40000000u))""")
 s=s.replace('    if(broad)extra_packets+=packets;','    if(ends){ngb_scene_count_ends(ends);fused_ends+=ends;}\n    if(broad)extra_packets+=packets;')
 s+='\nunsigned long long fifo_ends(void){return fused_ends;}\n'
if check:
 # Independently walk tagged packets one parameter at a time through the
 # actual scene hook, not the new method classification. Sample full spans
 # before handing control back to the regular parser.
 s=s.replace('unsigned long long fifo_extra_packets(void)', 'unsigned long long shadow_args,shadow_packets; static unsigned span_serial;\nunsigned long long fifo_extra_packets(void)')
 tag='    if(broad)extra_packets+=packets;'
 s=s.replace(tag,"""
 if(broad && ++span_serial%257==1){
   uint32_t check_regs[sizeof graph_regs/4],prev[sizeof graph_regs/4];
   memcpy(prev,graph_regs,sizeof prev);memcpy(check_regs,graph_regs,sizeof check_regs);
   unsigned pos=0,npack=0,args=0,shadow_ends=0;uint32_t endstate=0;
   while(pos<used){uint32_t h;memcpy(&h,mapped+off+4*pos++,4);
     unsigned n=(h&NV_PFIFO_CACHE1_DMA_STATE_METHOD_COUNT)>>18;
     unsigned m=h&NV_PFIFO_CACHE1_DMA_STATE_METHOD,noninc=(h>>30)&1u;
     if(!n || n>used-pos || ((h>>13)&7u) || m<0x200u)abort();
     for(unsigned j=0;j<n;j++){
       uint32_t val;memcpy(&val,mapped+off+4*pos++,4);
       if(m==NV097_SET_BEGIN_END){if(!val)++shadow_ends;} else if(!ngb_scene_method(check_regs,m,val,NULL))abort();
       if(!noninc)m=(m+4)&NV_PFIFO_CACHE1_DMA_STATE_METHOD;
     }
     endstate=m|noninc;++npack;args+=n;
   }
   if(memcmp(check_regs,prev,sizeof prev)||endstate!=*state||npack!=packets||args!=used-packets)abort();
   if(shadow_ends!=SHADOW_END_COUNT){abort();} shadow_args+=args;shadow_packets+=npack;
 }
 """+tag)
if check:s=s.replace('SHADOW_END_COUNT', 'ends' if fusion else '0')
o=p.compile('nv2a_boot.c',s);p.link[p.link.index(next(i for i in p.link if i.endswith('/nv2a_boot.c.o')))]=o
p.link.insert(1,'-Wl,--strip-debug');s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;'
if check:s=s.replace(k,k+' extern unsigned long long shadow_args,shadow_packets;if(!(scene_flips%120))fprintf(stderr,"[FIFO_CHECK] %u %llu %llu\\n",scene_flips,shadow_packets,shadow_args);')
if fusion:
 s+='\nvoid ngb_scene_count_ends(unsigned n){draws+=n;}\n'
 s=s.replace(k,k+' extern unsigned long long fifo_ends(void);if(!(scene_flips%120))fprintf(stderr,"[FUSED_END] %u %llu\\n",scene_flips,fifo_ends());')
p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);extern unsigned long long fifo_extra_packets(void);if(!(scene_flips%120))fprintf(stderr,"[RETIRED] %u %llu\\n",scene_flips,fifo_extra_packets());ngb_trial_flip(scene_flips,draws);'));p.finish()
