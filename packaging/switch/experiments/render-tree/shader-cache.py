"""Reuse immutable selected vertex programs. Compare exact program bytes,
including the final instruction, plus declaration object identity. The small
bounded cache owns both objects, so a freed address cannot become a hit."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
verify='--verify' in sys.argv
p=NativeProbe('shader-verify' if verify else 'shader-pair');p.driver((perf/'trial.inc').read_text())
s=(ROOT/'src/d3d/hle.cpp').read_text()
tag='std::shared_ptr<gpu::VertexShader> g_selected;'
s=s.replace(tag,'''extern "C" unsigned trial_variant;
struct SelectedSlot {uint32_t handle=0,at=0;std::shared_ptr<gpu::VertexShader> decl,vs;};
SelectedSlot slots[64];unsigned hits,misses;
'''+tag)
a=s.index('        auto vs = std::make_shared<gpu::VertexShader>();',s.index('case D3DF_D3DDevice_SelectVertexShader:'));b=s.index('        if (it != g_vs.end())',a)
s=s[:a]+'''        auto it=g_vs.find(h);
        auto *source=it==g_vs.end()?nullptr:it->second.get();
        SelectedSlot *slot=nullptr;
        bool hit=false;
        if (trial_variant) {
            slot=&slots[((h>>2)^at^(h>>11))&63];
            if(slot->vs && slot->handle==h && slot->at==at && slot->decl.get()==source) {
                auto &code=slot->vs->program;
                // Only code through the first FINAL instruction matters. If the
                // previous selection ran to the bank end its length is exact too.
                hit=code.empty() ? at>=136 : !std::memcmp(code.data(), &g_program[at][0],code.size()*sizeof(uint32_t));
            }
            if(hit){++hits;'''+('' if verify else '''g_selected=slot->vs;g_state.vs_handle=h|1;g_state.vs=g_selected;break;''')+'''}
            else ++misses;
        }
        auto vs=std::make_shared<gpu::VertexShader>();
'''+s[b:]
tag='        g_selected = vs;'
v='''        if(hit && (slot->vs->program!=vs->program || slot->vs->decl!=vs->decl || slot->vs->program_type!=vs->program_type || slot->vs->handle!=vs->handle)) std::abort();
''' if verify else ''
s=s.replace(tag,v+'''        if(slot){slot->handle=h;slot->at=at;slot->decl=it==g_vs.end()?nullptr:it->second;slot->vs=vs;}
'''+tag)
s=s.replace('    g_selected.reset();','    for(auto &slot:slots)slot=SelectedSlot{};\n    g_selected.reset();')
s+='\nextern "C" void selected_report(unsigned f){std::fprintf(stderr,"[SELECTED] %u %u %u\\n",f,hits,misses);}\n'
p.add('hle.cpp',s)
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;'
p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned),selected_report(unsigned);if(!(scene_flips%120))selected_report(scene_flips);ngb_trial_flip(scene_flips,draws);'));p.finish()
