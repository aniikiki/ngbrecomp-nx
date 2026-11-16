"""Specialize hot D3D mirror calls at their real function ID. Preserve both
the Xbox XDK body and active renderer; share Before's implementation with
the reference path instead of independently implementing state mutations."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
p=NativeProbe('render-dispatch');p.driver((perf/'trial.inc').read_text())
names=['SetStreamSource','SetTexture','LightEnable','SetLight','SetVertexShaderConstant1','SetVertexShaderConstant4','SetRenderState_TextureFactor','SetRenderState_Simple','SetVertexShader','SetRenderState_VertexBlend']
s=(ROOT/'src/d3d/hle.cpp').read_text()
tag='bool Before(int fn, Call c) {'
# Specializations only use the switches' surviving arm; do not clone a
# generic function containing 100+ dynamic arms at each call site.
assert s.count(tag)==1
s=s.replace(tag,'template<int Fixed=-1> bool Before(int runtime_fn, Call c) {\n    const int fn = Fixed==-1 ? runtime_fn : Fixed;')
k='extern "C" int d3d_hle_call(int fn, uint32_t regs[8]) {'
s=s.replace(k,'''extern "C" unsigned trial_variant;
extern "C" unsigned dispatch_hits;
unsigned dispatch_hits;
static int DirectMirror(int fn,uint32_t *regs){
 if(!g_started||!g_backend)return -1;
 bool handled=false;
 switch(fn){'''+''.join(f'case D3DF_D3DDevice_{x}:handled=Before<D3DF_D3DDevice_{x}>(fn,Call{{regs}});break;\n' for x in names)+'''
 default:return -1;}
 ++dispatch_hits;
 if(!handled && g_take[fn]){regs[EAX]=0;regs[ESP]+=4+g_take_ret[fn];handled=true;}
 return handled;
}
'''+k+'\n    if(trial_variant){int result=DirectMirror(fn,regs);if(result>=0)return result;}')
p.add('hle.cpp',s)
hooks=(RUNTIME/'direct/hooks.c').read_text()
k='    d3d_hle_after(fn, regs);'
hooks=hooks.replace(k,'''    extern unsigned trial_variant;
    if(!trial_variant) d3d_hle_after(fn, regs);
    else switch(fn){'''+''.join('case D3DF_D3DDevice_'+x+':\n' for x in names)+'''break;default:d3d_hle_after(fn,regs);}
''')
o=p.compile('direct/hooks.c',hooks,['-include',str(RUNTIME/'switch_guest_regs.h')])
p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=o
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;'
p.add('scene/bridge.c',s.replace(k,k+' extern unsigned dispatch_hits;extern void ngb_trial_flip(unsigned,unsigned); if(!(scene_flips%120))fprintf(stderr,"[FAST_DISPATCH] %u %u\\n",scene_flips,dispatch_hits);ngb_trial_flip(scene_flips,draws);'));p.finish()
