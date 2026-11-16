"""Adjacent 3078B0 parts: bypass constant preparation only after verifying live effective values."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'))
from native_probe import *
p=NativeProbe('opening-part-constants')
s=(RUNTIME/'direct/hooks.c').read_text();k='void ngb_direct_mesh_scope(int enter)\n{';assert s.count(k)==1
s=s.replace(k,'unsigned pc_part,pc_mode;\n'+k+'\n pc_part=enter && pc_mode && MEM32(esp)==0x003079CC && esi!=0;')
p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=p.compile('direct/hooks.c',s,['-include',str(RUNTIME/'switch_guest_regs.h')])
s='extern "C" {extern unsigned pc_part,pc_mode;unsigned pc_tests,pc_hits,pc_checks;}\n'+(ROOT/'src/d3d/hle.cpp').read_text()
k='    static_assert(n == 24);';assert s.count(k)==1
s=s.replace(k,k+r'''
    bool audit_hit=false;
    if(pc_part && pc_mode){
      ++pc_tests;std::array<float,4> sc,ofs;ViewportConstants(sc,ofs);
      if(!std::memcmp(dst,src,58*16) && !std::memcmp(dst+58*16,sc.data(),16) &&
         !std::memcmp(dst+59*16,ofs.data(),16) && !std::memcmp(dst+60*16,src+60*16,(192-60)*16)){
        ++pc_hits;
        if(pc_mode==1){g_state.changed_constant_blocks=0;++g_state.constants_revision;return;}
        audit_hit=true;
      }
    }
''')
k='    g_state.changed_constant_blocks = changes;';s=s.replace(k,'    if(audit_hit){if(changes)std::abort();++pc_checks;}\n'+k)
p.add('hle.cpp',s)
p.driver(r'''
extern unsigned pc_tests,pc_hits,pc_checks,pc_mode;
void pc_flip(unsigned f,unsigned draws){
 static uint64_t last;static unsigned prev;struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,pc_mode,(unsigned long long)(now-last),draws-prev);
 if(f==120)fprintf(stderr,"[PART_CONST] %u %u %u\n",pc_tests,pc_hits,pc_checks);
 pc_mode=f>=120?0:getenv("NGB_OPEN_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;prev=draws;}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void pc_flip(unsigned,unsigned);pc_flip({f},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
