"""Reuse the complete selected shader until a changed program write overlaps its range."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'))
from native_probe import *
p=NativeProbe('opening-selection-epoch')
s=(ROOT/'src/d3d/hle.cpp').read_text()
def edit(k,v):
 global s
 assert s.count(k)==1,k
 s=s.replace(k,v)
k='uint32_t g_program[136][4];'
edit(k,k+'''
extern "C" unsigned ep_arm;
struct SelectedEntry {uint32_t h,at,n;std::shared_ptr<gpu::VertexShader> decl,vs;};
static SelectedEntry ep[16];
static unsigned taken,attempts,checks,invalidations;
''')
a=s.index('        if (it != g_vs.end())\n            for (size_t i',s.index('case D3DF_D3DDevice_LoadVertexShader:'));b=s.index('        break;',a)
s=s[:a]+'''        if (it!=g_vs.end() && at<136){
            size_t n=std::min<size_t>(136-at,it->second->program.size()/4);
            if(n && std::memcmp(g_program[at],it->second->program.data(),16*n)){
               for(auto &e:ep)if(e.vs && e.at<at+n && at<e.at+e.n){e={};++invalidations;}
               std::memcpy(g_program[at],it->second->program.data(),16*n);
            }
        }
'''+s[b:]
k='        auto vs = std::make_shared<gpu::VertexShader>();\n        auto it = g_vs.find(h);'
edit(k,'''        auto it=g_vs.find(h);
        auto *decl=it==g_vs.end()?nullptr:it->second.get();
        auto &slot=ep[((h>>3)^(h>>10)^at)&15];
        bool hit=ep_arm && slot.vs && slot.h==h && slot.at==at && slot.decl.get()==decl;
        if(ep_arm)++attempts;
        if(hit){++taken;if(ep_arm==1){g_selected=slot.vs;g_state.vs_handle=h|1;g_state.vs=g_selected;break;}}
        auto vs=std::make_shared<gpu::VertexShader>();''')
k='        g_selected = vs;'
edit(k,'''        if(hit){
          auto &v=*slot.vs;if(v.handle!=vs->handle || v.program!=vs->program || v.decl!=vs->decl ||
            v.program_type!=vs->program_type || v.stream_stride!=vs->stream_stride || v.constants!=vs->constants)std::abort();
          for(unsigned i=0;i<v.inputs.size();++i){auto a=v.inputs[i],b=vs->inputs[i];if(a.stream!=b.stream||a.type!=b.type||a.offset!=b.offset)std::abort();}
          ++checks;
        }else if(ep_arm)slot={h,at,(unsigned)vs->program.size()/4,it==g_vs.end()?nullptr:it->second,vs};
'''+k)
edit('    g_selected.reset();','    for(auto &entry:ep)entry={};\n    g_selected.reset();')
# In the baseline arm run the exact original load; invalidate cached choices on every arm switch.
a=s.index('        if (it!=g_vs.end() && at<136)');b=s.index('        break;',a)
s=s[:a]+'''        if(!ep_arm){
          if(it!=g_vs.end())for(size_t i=0;i<it->second->program.size()/4 && at+i<136;i++)
            std::memcpy(g_program[at+i],&it->second->program[i*4],16);

        }else '''+s[a:b]+s[b:]
s+='\nextern "C" void ep_clear(){for(auto &entry:ep)entry={};}\nextern "C" void ep_report(){std::fprintf(stderr,"[EPOCH] %u %u %u %u\\n",attempts,taken,checks,invalidations);}\n'
p.add('hle.cpp',s)
p.driver(r'''
unsigned ep_arm;extern void ep_report(void),ep_clear(void);
void ep_flip(unsigned f,unsigned draws){
 static unsigned prev;static uint64_t last;struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,ep_arm,(unsigned long long)(now-last),draws-prev);
 if(f==120)ep_report();
 ep_arm=f>=120?0:getenv("NGB_OPEN_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));
 if(!ep_arm){ep_clear();} last=now;prev=draws;}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 edit(k,k+f' extern void ep_flip(unsigned,unsigned);ep_flip({f},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
