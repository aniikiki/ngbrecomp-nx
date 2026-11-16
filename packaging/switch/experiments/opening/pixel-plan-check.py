"""Exercise generated single-register fast path against actual ApplyPixelConstants."""
from pathlib import Path
import tempfile,subprocess,runpy
base=Path('src/d3d');s=runpy.run_path(str(Path(__file__).with_name('pixel-write-plan.py')))['transform']((base/'hle.cpp').read_text())
plan=s[s.index('struct PlannedPixel'):s.index('const PlannedPixel* active_pixel_plan')]
body=s[s.index('auto apply=[&]()'):s.index('            if(check){',s.index('auto apply=[&]()'))]
t=(base/'gpu/texture.cpp').read_text();ref=t[t.index('uint32_t PackColor('):t.index('}  // namespace gpu',t.index('uint32_t PackColor('))]
src='''#include <algorithm>
#include <cassert>
#include <cstring>
#include <cstdio>
#include <random>
#include "gpu/state.h"
namespace gpu {
'''+ref+'}\n'+plan+'''
int main(){std::mt19937 rng(412);unsigned tests=0;
for(unsigned d=0;d<260;d++){auto shader=std::make_shared<PlannedPixel>();
for(unsigned i=57;i<=59;i++)shader->def[i]=d<16?0x11111111u*d:rng();shader->prepare();
gpu::State g_state;g_state.ps=shader;auto active_pixel_plan=shader.get();
for(unsigned reg=0;reg<8;reg++){for(auto &c:g_state.psc[reg])c=(int(rng()%500)-125)/255.f;
for(auto &v:g_state.simple)v=rng();gpu::State expected=g_state;
gpu::ApplyPixelConstants(expected,reg,1);
'''+body+'''apply();assert(g_state.simple==expected.simple);++tests;}}
printf("%u complete register arrays equal\\n",tests);}
'''
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'check.cpp';f.write_text(src);subprocess.run(['c++','-std=c++17','-O2','-I'+str(base.resolve()),str(f),'-o',tmp+'/test'],check=True);subprocess.run([tmp+'/test'],check=True)
