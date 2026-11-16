"""Exercise actual generated constant-offset stores and fallback against original loop."""
from pathlib import Path
import runpy,tempfile,subprocess
src=Path('src/d3d/hle.cpp').read_text()
new=runpy.run_path(str(Path(__file__).with_name('simple-literal.py')))['transform'](src)
def segment(s,k):
 a=s.index(k);return s[a:s.index('    for (int s = 0;',a)]
a=segment(src,'    for (uint32_t i = 0; i < gpu::kRsDeferredFirst');b=segment(new,'    static constexpr uint32_t expected_methods')
literal=b.split('expected_methods[]=')[1].split(';')[0]
c='''
#include <array>
#include <cstdint>
#include <cstring>
#include <cassert>
namespace gpu {constexpr unsigned kRsDeferredFirst=92;}
struct State{std::array<uint32_t,2048>simple;}g_state;
unsigned rng=9;unsigned roll(){return rng=1664525*rng+1013904223;}
'''
for n,s in [('ref',a),('cand',b)]:c+='void '+n+'(const uint32_t* methods,const uint32_t* states){'+s+'}\n'
c+='int main(){const uint32_t base[]='+literal+''';uint32_t methods[92],states[92];
 for(int test=0;test<24000;++test){memcpy(methods,base,sizeof methods);
 if(test%3)methods[(test/3)%92]=test%3==1?0x1d78:roll();
 for(auto&x:states)x=roll();for(auto&x:g_state.simple)x=roll();
 auto orig=g_state;ref(methods,states);auto expect=g_state;
 g_state=orig;cand(methods,states);assert(expect.simple==g_state.simple);}}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'t.cpp';p.write_text(c)
 subprocess.run(['c++','-std=c++17','-O2',p,'-o',p.with_suffix('')],check=True)
 subprocess.run([p.with_suffix('')],check=True)
print('24000 complete state comparisons passed')
