"""Resolve ordinary guest render state once per contiguous range; verify live addresses."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
s=(ROOT/'src/d3d/hle.cpp').read_text()
s='extern "C" {extern unsigned span_arm;extern unsigned char* ngb_fast_ram;}\n'+s
i=s.index('void SyncDrawConstants()')
s=s[:i]+'''static unsigned span_calls,span_hits,span_checked;
template<uint32_t A> static inline void* StaticState(){
 static_assert(A>=0x8000 && A+4096<0x01000000);
 if(!span_arm || !ngb_fast_ram)return HostPtr(A);
 auto *p=ngb_fast_ram+A;
 if(span_arm==2 && p!=HostPtr(A))std::abort();
 return p;
}
'''+s[i:]
for tag in ['kVsConstants','kRenderState + gpu::kRsDeferredFirst * 4','kSimpleEncode','kRenderState','kTextureState + s * 32 * 4']:
 a=s.index('void SyncDrawConstants()');b=s.index('gpu::Surface SurfaceOf',a)
 alt='StaticState<'+tag+'>()' if ' + s ' not in tag else '(span_arm ? static_cast<uint8_t*>(StaticState<kTextureState>())+s*128 : HostPtr(kTextureState + s * 32 * 4))'
 s=s[:a]+s[a:b].replace('HostPtr('+tag+')',alt)+s[b:]
k='        for (uint32_t t = 0; t < 10; t++) {'
assert s.count(k)==1
s=s.replace(k,'''        if(span_arm){
            ++span_calls;
            const uint32_t base=dev+0xC60;
            // Device state is 640 bytes of matrices followed by the material.
            // Test every touched low page against its live backing; no guest
            // calls or yields between the guards and the copies.
            if(dev<=0x04000000u-0xf44 && ngb_fast_ram &&
               ngb_direct_pages[base>>12]==ngb_fast_ram+(base&~4095u) &&
               ngb_direct_pages[(dev+0xf43)>>12]==ngb_fast_ram+((dev+0xf43)&~4095u)){
                ++span_hits;auto *v=ngb_fast_ram+base;
                static_assert(sizeof(g_state.transforms[0])==64);
                if(span_arm==2){
                    for(unsigned t=0;t<10;t++)if(HostPtr(base+64*t)!=v+64*t)std::abort();
                    if(HostPtr(dev+0xf00)!=v+0x2a0)std::abort();
                }
                std::memcpy(&g_state.transforms[2],v,128);
                std::memcpy(&g_state.transforms[16],v+128,256);
                std::memcpy(&g_state.transforms[256],v+384,256);
                std::memcpy(g_state.material.data(),v+0x2a0,68);
                if(span_arm==2){
                    for(unsigned t=0;t<10;t++)if(std::memcmp(g_state.transforms[t<2?t+2:t<6?t+14:t+250].data(),HostPtr(base+64*t),64))std::abort();
                    if(std::memcmp(g_state.material.data(),HostPtr(dev+0xf00),68))std::abort();
                    ++span_checked;
                }
                return;
            }
        }
'''+k)
s+='\nextern "C" void span_report(){fprintf(stderr,"[STATE_SPAN] %u %u %u\\n",span_calls,span_hits,span_checked);}\n'
p.add('hle.cpp',s)
p.driver(r'''
unsigned span_arm;
extern void span_report(void);
void span_frame(unsigned f,unsigned draws){
 static uint64_t last;static unsigned prev;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
 uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,span_arm,(unsigned long long)(now-last),draws-prev);
 if(f==120)span_report();
 span_arm=f>=120?0:getenv("NGB_OPEN_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;prev=draws;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void span_frame(unsigned,unsigned);span_frame({arg},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
