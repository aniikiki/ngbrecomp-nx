from pathlib import Path
import subprocess,tempfile,runpy
d=Path(__file__).parent
s=runpy.run_path(str(d/'constant-groups.py'))['transform'](Path('src/d3d/hle.cpp').read_text())
impl=s[s.index('template<unsigned First,unsigned Count,unsigned Block>\nstatic inline uint32_t ResolveDifferent'):s.index('void SyncDrawConstants() {')]
base=Path('src/d3d/gpu/sync_constants.h').resolve()
code='#include <array>\n#include <cassert>\n#include "'+str(base)+'"\n'+impl+'''
template<unsigned F,unsigned C>void check(){
 constexpr unsigned B=128;std::array<uint8_t,24*B+2>src{},a{},b{};
 for(unsigned mask=0;mask<(1u<<C);++mask)for(unsigned j=0;j<B;++j){
  for(unsigned i=0;i<C;++i)if(mask>>i&1)src[1+(F+i)*B+j]^=255;
  auto x=gpu::SyncConstantRange<F,C,B>(a.data()+1,src.data()+1);
  auto y=SyncGroups<F,C,B>(b.data()+1,src.data()+1);
  assert(x==(mask<<F) && y==x && a==b);
 }}
int main(){check<0,7>();check<8,8>();check<16,8>();}
'''
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'x.cpp';f.write_text(code)
 subprocess.run(['c++','-O2','-std=c++17',f,'-o',f.with_suffix('')],check=True)
 subprocess.run([f.with_suffix('')],check=True)
print('81920 mask and byte-offset comparisons passed')
