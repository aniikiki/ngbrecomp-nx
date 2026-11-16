"""Cache only the combiner destinations and packed color, always write mapped outputs."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
s=(ROOT/'src/d3d/hle.cpp').read_text()
k='        gpu::ApplyPixelConstants(g_state, reg, n);'
assert s.count(k)==1
s=s.replace(k,'''        extern unsigned opening_arm,opening_verified,opening_hits;
        if(opening_arm && n==1 && reg<8 && g_state.ps && R32(c.r[ESP])>=0x1d70a8 && R32(c.r[ESP])<=0x1d70cd){
            struct Slot { bool valid=false; unsigned mapping[3]{},dest[18]{},len=0;
                std::array<float,4> value{}; uint32_t packed=0;};
            static Slot slots[8];auto &slot=slots[reg];
            const auto *mapping=g_state.ps->def+57;
            if(!slot.valid || std::memcmp(slot.mapping,mapping,12)){
                std::memcpy(slot.mapping,mapping,12);slot.len=0;
                for(unsigned i=0;i<8;i++){
                    if(((mapping[0]>>(4*i))&15)==reg)slot.dest[slot.len++]=gpu::kMPsConstant0/4+i;
                    if(((mapping[1]>>(4*i))&15)==reg)slot.dest[slot.len++]=gpu::kMPsConstant1/4+i;
                }
                if((mapping[2]&15)==reg)slot.dest[slot.len++]=gpu::kMPsFinalConstant0/4;
                if(((mapping[2]>>4)&15)==reg)slot.dest[slot.len++]=gpu::kMPsFinalConstant1/4;
            }
            if(!slot.valid || std::memcmp(slot.value.data(),g_state.psc[reg].data(),16)){
                slot.value=g_state.psc[reg];slot.packed=gpu::PackColor(slot.value);
            }else ++opening_hits;
            slot.valid=true;
            if(opening_arm==2){
                const auto before=g_state.simple;
                gpu::ApplyPixelConstants(g_state,reg,n);
                const auto expected=g_state.simple;g_state.simple=before;
                for(unsigned j=0;j<slot.len;j++)g_state.simple[slot.dest[j]]=slot.packed;
                if(expected!=g_state.simple)std::abort();
                ++opening_verified;
            }else for(unsigned j=0;j<slot.len;j++)g_state.simple[slot.dest[j]]=slot.packed;
        }else gpu::ApplyPixelConstants(g_state,reg,n);''')
k='void SyncDeferred() {'
s=s.replace(k,'unsigned opening_arm,opening_verified,opening_hits;\n'+k)+'''
extern "C" void opening_pixel_frame(unsigned f,unsigned draws){
 static uint64_t last; static unsigned previous;struct timespec t;
 clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f && last)std::fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\\n",f,opening_arm,(unsigned long long)(now-last),draws-previous);
 if(f==120)std::fprintf(stderr,"[OPEN_PIXEL] checked=%u value_hits=%u\\n",opening_verified,opening_hits);
 static bool check=std::getenv("NGB_OPEN_CHECK")!=nullptr;
 static unsigned seed=std::getenv("NGB_OPEN_REVERSE")?1:0;
 opening_arm=check?2:(((f/2+12345)*2654435761u>>31)^(f&1)^seed);
 last=now;previous=draws;
}
'''
p.driver('');p.add('hle.cpp',s)
s=(RUNTIME/'scene/bridge.c').read_text()
for k,call in [('            ngb_direct_reset_stats();','opening_pixel_frame(0,draws);'),('    ++scene_flips;','opening_pixel_frame(scene_flips,draws);')]:
 assert s.count(k)==1;s=s.replace(k,k+' extern void opening_pixel_frame(unsigned,unsigned);'+call)
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
