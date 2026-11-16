"""Execute extracted reference and candidate load/select bodies across writes,
overwriting a terminator, declaration replacement, cache evictions and resets."""
from pathlib import Path
import runpy,subprocess as sp,tempfile,sys
bulk="--program-range" in sys.argv
root=Path(__file__).resolve().parents[4]
s=(root/'src/d3d/hle.cpp').read_text()
v=runpy.run_path(str(Path(__file__).with_name('program-range.py' if bulk else 'shader-bank.py')))['transform'](s)
out='''
#include <algorithm>
#include <array>
#include <memory>
#include <vector>
#include <unordered_map>
#include <cstring>
#include <cstdint>
#include <cassert>
namespace gpu {struct VertexShader{unsigned handle=0,program_type=0;std::vector<unsigned> decl,inputs,stream_stride,program;};}
enum {EAX,EBX,D3DF_D3DDevice_LoadVertexShader,D3DF_D3DDevice_SelectVertexShader};
struct Call {unsigned r[2];unsigned a(int){return r[1];}};
'''
for name,src in [('ref',s),('candidate',v)]:
 a=src.index('uint32_t g_program[');b=src.index('std::shared_ptr<gpu::VertexShader> g_selected;',a)
 out+='namespace '+name+'{\n'+src[a:b]+'''
std::shared_ptr<gpu::VertexShader> g_selected;
std::unordered_map<unsigned,std::shared_ptr<gpu::VertexShader>> g_vs;
struct {unsigned vs_handle;std::shared_ptr<gpu::VertexShader> vs;}g_state;
void run(unsigned fn,Call c){switch(fn){
'''+src[src.index('    case D3DF_D3DDevice_LoadVertexShader:'):src.index('    case D3DF_D3DDevice_SetPixelShader:')]+'''}}\n}\n'''
out+='''
unsigned seed=7;unsigned rnd(){return seed=seed*1664525u+1013904223u;}
int main(){
for(unsigned i=0;i<50000;i++){
 unsigned h=(rnd()>>16)%96,at=(rnd()>>16)%150;
 if(i%3==0){
  auto vs=std::make_shared<gpu::VertexShader>();
  vs->decl={rnd()};vs->inputs={rnd()};vs->stream_stride={rnd()};
  for(unsigned j=0,n=rnd()%160;j<n;j++){vs->program.insert(vs->program.end(),{rnd(),rnd(),rnd(),rnd()>>26});}
  ref::g_vs[h]=vs;candidate::g_vs[h]=vs;
 }
 if(i%5==0||i%17==0){ref::run(2,{h,at});candidate::run(2,{h,at});}
 for(int j=0;j<2;j++){
 ref::run(3,{h,at});candidate::run(3,{h,at});
 auto &a=*ref::g_selected,&b=*candidate::g_selected;
 assert(!memcmp(ref::g_program,candidate::g_program,sizeof ref::g_program));
 assert(a.program==b.program&&a.handle==b.handle&&a.program_type==b.program_type&&a.decl==b.decl&&a.inputs==b.inputs&&a.stream_stride==b.stream_stride&&ref::g_state.vs_handle==candidate::g_state.vs_handle);
 }
 if(i%999==0){candidate::bank_epoch=UINT64_MAX;candidate::invalidate_bank();}
}
}
'''
if bulk:
 out=out.replace('if(i%999==0){candidate::bank_epoch=UINT64_MAX;candidate::invalidate_bank();}', '')
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'bank.cpp';f.write_text(out);exe=f.with_suffix('')
 sp.run(['c++','-std=c++17','-O2',f,'-o',exe],check=True);sp.run([exe],check=True)
print('100000 original/candidate selections match')
