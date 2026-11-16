"""Bypass all index-list assembly for one verified packed draw; oracle and flipped A/B."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'))
from native_probe import *
p=NativeProbe('opening-push-shape')
s=(ROOT/'src/d3d/hle.cpp').read_text()
k='void RunPushBuffer(uint32_t pb) {'
assert s.count(k)==1
s='extern "C"{extern unsigned ps_arm;unsigned ps_total,ps_taken,ps_checked;extern unsigned char* ngb_fast_ram;extern unsigned short ngb_fast_page_bytes[];extern unsigned char ngb_target_pages[];}\n'+s.replace(k,(h/'push-shape.inc').read_text()+'\n'+k)
k='    std::vector<uint16_t> idx;';assert s.count(k)==1
s=s.replace(k,'''    unsigned pp=0,nn=0,checks=0;const uint8_t *ptr=nullptr;bool audit=false;
    if(ps_arm){++ps_total;if(direct_packet(data,size,pp,nn,ptr)){
      ++ps_taken;if(ps_arm==1){Draw(pp,0,nn,ptr);return;}audit=true;
    }}
    auto emit=[&](unsigned prim,const std::vector<uint16_t>& idx){
      if(audit){if(checks++ || pp!=prim || nn!=idx.size() || std::memcmp(ptr,idx.data(),2*nn))std::abort();++ps_checked;}
      Draw(prim,0,uint32_t(idx.size()),reinterpret_cast<const uint8_t*>(idx.data()));
    };
'''+k)
k='Draw(prim, 0, uint32_t(idx.size()), reinterpret_cast<const uint8_t*>(idx.data()));';assert s.count(k)==2;s=s.replace(k,'emit(prim,idx);')
k='if (prim && !idx.empty()) emit(prim,idx);';s=s.replace(k,k+'\n    if(audit&&checks!=1)std::abort();')
p.add('hle.cpp',s)
p.driver(r'''
unsigned ps_arm;extern unsigned ps_total,ps_taken,ps_checked;
void ps_flip(unsigned f,unsigned draws){
 static unsigned prev;static uint64_t last;struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,ps_arm,(unsigned long long)(now-last),draws-prev);
 if(f==120)fprintf(stderr,"[PACKET] %u %u %u\n",ps_total,ps_taken,ps_checked);
 ps_arm=f>=120?0:getenv("NGB_OPEN_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;prev=draws;}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void ps_flip(unsigned,unsigned);ps_flip({f},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
