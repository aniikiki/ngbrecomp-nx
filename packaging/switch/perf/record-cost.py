"""Profile intact draws; measure only the calling thread, including nested recording."""
from pathlib import Path
from native_probe import NativeProbe, ROOT as root, RUNTIME as rt
import sys
opening = '--opening' in sys.argv
lo, hi = (1,120) if opening else (1801,1920)
probe=NativeProbe('opening-setup' if opening else 'record-cost')
probe.driver('''unsigned cost_frame; unsigned long long cost_sums[10]; unsigned cost_n,cost_seen,cost_counts[10];
void cost_flip(unsigned f){
    if(f>=1801 && f<=1920){
        fprintf(stderr,"[RECORD_COST] %u %u %u",f,cost_seen,cost_n);
        for(unsigned i=0;i<10;i++)fprintf(stderr," %llu",cost_sums[i]);
        for(unsigned i=0;i<10;i++)fprintf(stderr," %u",cost_counts[i]);
        fputc(10,stderr);
    }
    memset(cost_counts,0,sizeof cost_counts);memset(cost_sums,0,sizeof cost_sums);cost_frame=f+1;cost_n=cost_seen=0;
}
'''.replace('1801',str(lo)).replace('1920',str(hi)))

h='''#include <time.h>
extern "C" { extern unsigned cost_frame,cost_n,cost_seen,cost_counts[10];extern unsigned long long cost_sums[10];extern thread_local int sample_cost; }
static unsigned long long ccost(){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return (unsigned long long)t.tv_sec*1000000000+t.tv_nsec;}
struct CostSpan{unsigned k;unsigned long long t;CostSpan(unsigned i):k(i),t(sample_cost==int(i)?ccost():0){}~CostSpan(){if(t){cost_sums[k]+=ccost()-t;++cost_counts[k];}}};
'''
s=(root/'src/d3d/hle.cpp').read_text()
tag='    if (!g_backend) return;\n    bool measure ='
assert s.count(tag)==1
s=s.replace(tag,'''    if (!g_backend) return;
    struct Sampler{int prev=sample_cost;~Sampler(){sample_cost=prev;}} outer;
    sample_cost=-1;
    if(cost_frame>=1801 && cost_frame<=1920){
        ++cost_seen;static unsigned rng=157; rng=1664525u*rng+1013904223u;
        if((rng>>29)==0){sample_cost=((unsigned long long)(rng & 0x1fffffffu)*10)>>29;++cost_n;}}
    CostSpan total(0); {CostSpan clock_control(9);}
    bool measure =''')
s=s.replace('    SyncDeferred();','    {CostSpan sync(1);SyncDeferred();}')
s=s.replace('cost_frame>=1801 && cost_frame<=1920',f'cost_frame>={lo} && cost_frame<={hi}')
probe.add('hle.cpp',h+'extern "C" { thread_local int sample_cost=-1; }\n'+s)
s=(root/'src/d3d/gpu/threaded.cpp').read_text()
def once(tag,repl):
 global s
 assert s.count(tag)==1,tag
 s=s.replace(tag,repl)
once('        SendState(s, start + count);','        { CostSpan state(2); SendState(s, start + count); }')
once('        Cmd c{Op::Draw};','        CostSpan rest(8); Cmd c{Op::Draw};')
once('        for (int i = 0; i < 4; i++) {\n            SendHeader','        { CostSpan headers(3); for (int i = 0; i < 4; i++) {\n            SendHeader')
once('        FlushHeaders();\n        SendPeek(s);','        FlushHeaders(); }\n        {CostSpan peek(4);SendPeek(s);}')
once('        SendFixedRanges(now,','        {CostSpan fixed(5);SendFixedRanges(now,')
once('std::make_index_sequence<kStateRanges.size()>{});','std::make_index_sequence<kStateRanges.size()>{});}')
once('        const size_t constant_offset','        {CostSpan constants(6);const size_t constant_offset')
once('        constants_source_ = &s;', '        }\n        CostSpan tail(7); constants_source_ = &s;')
probe.add('threaded.cpp',h+s)
s=(rt/'scene/bridge.c').read_text()
tag='    ++scene_flips;'
assert s.count(tag)==1
if opening:
    start='            ngb_direct_reset_stats();'
    assert s.count(start)==1
    s=s.replace(start,start+' extern void cost_flip(unsigned);cost_flip(0);')
    probe.link.insert(1,'-Wl,--strip-debug')
probe.add('scene/bridge.c',s.replace(tag,tag+' extern void cost_flip(unsigned);cost_flip(scene_flips);'))
probe.finish()
