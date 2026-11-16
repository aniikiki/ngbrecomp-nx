"""Measure the real texture signatures on the render thread; do not bypass hashing."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-texture-hash')
s=(ROOT/'src/d3d/vk/backend.cpp').read_text()
def patch(old,new):
 global s
 assert s.count(old)==1,old
 s=s.replace(old,new)
k='static uint64_t TextureSignature('
patch(k,r'''
struct HashBudget { uint64_t hits,body,bytes,ns,known,same,adj,sbytes,sns,pal,pns,cal; };
static HashBudget hb{};
static uint64_t hclock(){timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return uint64_t(t.tv_sec)*1000000000+t.tv_nsec;}
static void hash_frame(unsigned f) {
 if(f<=120)std::fprintf(stderr,"[HASHFRAME] %u %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu\n",f,
 (unsigned long long)hb.hits,(unsigned long long)hb.body,(unsigned long long)hb.bytes,(unsigned long long)hb.ns,
 (unsigned long long)hb.known,(unsigned long long)hb.same,(unsigned long long)hb.adj,(unsigned long long)hb.sbytes,
 (unsigned long long)hb.sns,(unsigned long long)hb.pal,(unsigned long long)hb.pns,(unsigned long long)hb.cal);
 hb={};
}
'''+k)
patch('            sig = m.sig;\n        } else','            ++hb.hits; sig = m.sig;\n        } else')
k='                m.sig = TextureSignature(guest, bytes, uint64_t(d.format) << 32 | d.width << 16 | d.height);'
patch(k,'''                auto ca=hclock();auto cb=hclock();auto prev=m.sig;
                auto a=hclock();
'''+k+'''
                auto elapsed=hclock()-a; hb.cal+=cb-ca;++hb.body;hb.ns+=elapsed;hb.bytes+=bytes;
                if(m.frame){++hb.known;if(prev==m.sig){++hb.same;hb.adj+=m.frame==frame_;hb.sbytes+=bytes;hb.sns+=elapsed;}}
''')
patch('        sig = Hash(palette, 1024, sig);','        auto ca=hclock();auto cb=hclock();auto a=hclock();sig = Hash(palette, 1024, sig);hb.pns+=hclock()-a;++hb.pal;hb.cal+=cb-ca;')
patch('    frame_++;','    hash_frame(frame_+1);frame_++;')
obj=p.compile('vk/backend.cpp','#include <time.h>\n'+s,['-DNGB_RIGID_CLIP'])
p.link[p.link.index(str(REGS/'backend-host-clip.o'))]=obj
# Let the guest run a few extra flips: worker can lag; require all 120 presents in report.
ds=(REGS/'host-driver.c').read_text();k='        ngb_stop("verified 120 original demo frames", 120);'
assert ds.count(k)==1
ds=ds.replace(k,'        fprintf(stderr,"[HASH_WINDOW] guest reached 120 with motion\\n");')
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';assert s.count(k)==1
p.add('scene/bridge.c',s.replace(k,k+' if(scene_flips==124)ngb_stop("completed hash diagnostic",124);'))
p.link[p.link.index(str(p.core/'exact-runtime_test.c.o'))]=p.compile('runtime_test.c',ds,['-I'+str(REGS),'-I'+str(RUNTIME),'-include',str(RUNTIME/'switch_guest_regs.h'),'-DNGB_RIGID_CLIP','-DNGB_REGISTER_PACKAGE'])
p.link.insert(1,'-Wl,--strip-debug');p.finish()
