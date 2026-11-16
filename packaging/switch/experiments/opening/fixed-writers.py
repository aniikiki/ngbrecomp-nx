"""Offline paired opening replay: skip only recorder ranges with known HLE writers."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parents[1]/'perf'))
from native_probe import NativeProbe,ROOT,RUNTIME
p=NativeProbe('opening-fixed-writers')
def edit(s,key,rep):
    assert s.count(key)==1,key
    return s.replace(key,rep)
decl='extern "C" {extern unsigned fw_mode,fw_dirty,fw_skips,fw_checks;extern const void *fw_source;}\n'
s=decl+(ROOT/'src/d3d/hle.cpp').read_text()
# Rs/tss, ordinary simple methods, matrix and material can be written inline
# by the title. Leave those ranges on the existing per-draw path.
for key,bits in [('        g_state.simple[(c.r[ECX]',0x2d),
 ('        const uint32_t* d = ps->def;',0x2d),
 ('        gpu::ApplyPixelConstants(g_state',0x12d),
 ('        if (c.a(0)) g_state.rt',0x4100),
 ('        uint32_t v = c.a(0);\n        float mn',0x100),
 ('        g_state.scissor_count = std::min',0x100),
 ('        if (g_state.rt.header) g_state.rt',0x100),
 ('        g_state.ss_offset_x = c.af',0x2000),
 ('            g_state.light_enable =',0x2000),
 ('        g_state.vs_handle = h;',0x80),('        g_state.vs_handle = h | 1;',0x80)]:
    if 'g_state.light_enable' in key:
        key='    case D3DF_D3DDevice_LightEnable:'
        rep=key+f'\n        if(fw_mode) fw_dirty |= {bits};'
    else:rep=f'        if(fw_mode) fw_dirty |= {bits};\n'+key
    s=edit(s,key,rep)
s=s.replace('    g_state = gpu::State{};', '    fw_source=&g_state;fw_dirty=~0u;g_state = gpu::State{};')
s=edit(s,'void Start() {','void Start() { fw_source=&g_state;fw_dirty=~0u;')
p.add('hle.cpp',s)
s=decl+(ROOT/'src/d3d/gpu/threaded.cpp').read_text()
key='        // These fixed-size comparisons fold'
s=edit(s,key,'''        constexpr unsigned tracked=0x61ad; // ranges 0,2,3,5,7,8,13,14
        if constexpr(tracked & (1u<<I)){
            if(fw_mode && fw_source==now && !(fw_dirty&(1u<<I))){
                if(fw_mode==2){++fw_checks;if(std::memcmp(previous,now+r.off,r.len))std::abort();}
                if(fw_mode==2)++fw_skips;
                return;
            }
        }
'''+key)
key='        SendFixedRanges(now, std::make_index_sequence<kStateRanges.size()>{});'
s=edit(s,key,key+'\n        fw_dirty=(fw_source==now && fw_mode)?0:~0u;')
key='    void SendState(const State& s, uint32_t vertices) {'
s=edit(s,key,key+'\n        if(!fw_seen_){fw_seen_=true;fw_dirty=~0u;}')
s=edit(s,'    bool peek_sent_ = false;', '    bool fw_seen_=false;\n    bool peek_sent_ = false;')
p.add('threaded.cpp',s)
p.driver(r'''
unsigned fw_mode,fw_dirty=~0u,fw_checks,fw_skips;const void *fw_source;
void fw_flip(unsigned f,unsigned draws){
 static unsigned prev;static uint64_t last;struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,fw_mode,(unsigned long long)(now-last),draws-prev);
 if(f==120 && fw_mode==2 && !fw_checks)__builtin_abort();
 if(f==120)fprintf(stderr,"[WRITER_CHECK] %u %u\n",fw_checks,fw_skips);
 unsigned next=f>=120?0:getenv("NGB_OPEN_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));
 if(next!=fw_mode){fw_dirty=~0u;}fw_mode=next;last=now;prev=draws;}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
    s=edit(s,k,k+f' extern void fw_flip(unsigned,unsigned);fw_flip({f},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
