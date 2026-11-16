"""Allocate the selected shader's program exactly once. Keep object ownership,
declaration and command ordering identical, including handles recycled by the title."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent;perf=here.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import NativeProbe,ROOT,RUNTIME
verify='--verify' in sys.argv
p=NativeProbe('shader-alloc-check' if verify else 'shader-alloc-pair')
p.driver((perf/'trial.inc').read_text());s=(ROOT/'src/d3d/hle.cpp').read_text()
a=s.index('        for (uint32_t i = at; i < 136; i++)',s.index('case D3DF_D3DDevice_SelectVertexShader:'))
b=s.index('        vs->handle',a)
orig=s[a:b]
fast="""        if(at<136) {
            uint32_t end=at;
            do {++end;} while(end<136 && !(g_program[end-1][3]&1u));
            vs->program.resize((end-at)*4);
            std::memcpy(vs->program.data(),g_program[at],(end-at)*sizeof(g_program[0]));
        }
"""
s=s[:a]+'        if (trial_variant) { ++alloc_trials;\n'+fast+('std::vector<uint32_t> ref;\n'+orig.replace('vs->program','ref')+'if(ref!=vs->program)std::abort();\n' if verify else '')+'} else {\n'+orig+'}\n'+s[b:]
s='extern "C" unsigned trial_variant; static unsigned alloc_trials;\n'+s+'\nextern "C" void alloc_report(unsigned f){std::fprintf(stderr,"[ALLOC_TRIAL] %u %u\\n",f,alloc_trials);}\n'
p.add('hle.cpp',s)
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;'
p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned),alloc_report(unsigned);if(!(scene_flips%120))alloc_report(scene_flips);ngb_trial_flip(scene_flips,draws);'));p.link.insert(1,'-Wl,--strip-debug');p.finish()
