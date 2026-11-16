"""Keep previously initialized batch bytes on recycle. Never read stale alignment padding."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'))
from native_probe import *
p=NativeProbe('opening-index-arena')
s=(ROOT/'src/d3d/gpu/threaded.cpp').read_text()
k='struct Batch {';assert s.count(k)==1
s=s.replace(k,r'''
extern "C" {extern unsigned ia_mode,ia_writes;extern unsigned long long ia_bytes;}
struct BatchBytes {
 std::vector<uint8_t> store;size_t used=0;
 size_t size()const{return used;}
 auto data(){return store.data();}auto data()const{return store.data();}
 void resize(size_t next){
    if(!ia_mode || next>store.size())store.resize(next);
    else if(ia_mode==2 && next>used){++ia_writes;ia_bytes+=next-used;std::memset(data()+used,0xa5,next-used);}
    used=next;
 }
 void clear(){used=0;} // render thread does not read the mode or reset allocated storage
};
'''+k)
a=s.index(k);i=s.index('std::vector<uint8_t> bytes;',a);s=s[:i]+s[i:].replace('std::vector<uint8_t> bytes;','BatchBytes bytes;',1)
k='        cur_->bytes.resize(at + n);';assert s.count(k)==1
s=s.replace(k,'        size_t old=cur_->bytes.size();\n'+k+'\n        if(at>old)std::memset(cur_->bytes.data()+old,0,at-old);')
# baseline must zero any logically fresh bytes even if store survived a clear, as std::vector originally did.
s=s.replace('if(!ia_mode || next>store.size())store.resize(next);','if(!ia_mode){store.resize(used);store.resize(next);}else if(next>store.size())store.resize(next);')
p.add('threaded.cpp',s)
p.driver(r'''
unsigned ia_mode,ia_writes;unsigned long long ia_bytes;
void ia_flip(unsigned f,unsigned draws){
 static uint64_t last;static unsigned prev;struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,ia_mode,(unsigned long long)(now-last),draws-prev);
 if(f==120)fprintf(stderr,"[INDEX_ARENA] writes=%u bytes=%llu\n",ia_writes,ia_bytes);
 ia_mode=f>=120?0:getenv("NGB_OPEN_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));last=now;prev=draws;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void ia_flip(unsigned,unsigned);ia_flip({f},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
