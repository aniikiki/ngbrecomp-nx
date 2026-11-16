from pathlib import Path
import runpy,subprocess as sp,tempfile
p=Path(__file__).resolve().parent
src=runpy.run_path(str(p/'fixed-mask-packet.py'))['transform']((p.parents[3]/'src/d3d/gpu/threaded.cpp').read_text())
a=src.index('    template<size_t... I>\n    void PackFixed');b=src.index('    // what changed since',a)
lengths=[32,256,132,4,4,8,1336,4,196,128,256,256,68,20,4];offset=3;ranges=[]
for n in lengths:ranges.append((offset,n));offset+=n+5
c='''#include <cassert>
#include <array>
#include <cstdint>
#include <cstring>
#include <type_traits>
#include <utility>
#include <vector>
struct Range{size_t off,len;};
struct Cmd{uint32_t c=0;};
constexpr std::array<Range,15> kStateRanges={{'''+','.join('{%d,%d}'%r for r in ranges)+'''}};
struct R { unsigned char sent_[4096]={};struct B{std::vector<uint8_t> bytes;};B*cur_;
'''+src[a:b]+'''};
int main(){R r{};R::B batch;r.cur_=&batch;
std::array<uint8_t,4096> state{},now{},expected{};
for(unsigned mask=0;mask<(1<<15);mask++){batch.bytes.assign(3,0x9e);
for(unsigned i=0;i<15;i++){auto g=kStateRanges[i];if(mask>>i&1)now[g.off+mask%g.len]^=92;
std::memcpy(expected.data()+g.off,now.data()+g.off,g.len);}
Cmd cmd;r.PackFixed(now.data(),cmd,std::make_index_sequence<15>{});assert(cmd.c==mask);
auto fixed=batch.bytes.size();uint32_t h[]={4001,3};auto p=(const uint8_t*)h;
batch.bytes.insert(batch.bytes.end(),p,p+8);batch.bytes.insert(batch.bytes.end(),{2,3,4});
auto end=r.UnpackFixed(cmd.c,batch.bytes.data()+3,state.data(),std::make_index_sequence<15>{});
assert(end==batch.bytes.data()+fixed && !std::memcmp(end,h,8));
assert(state==expected && !std::memcmp(r.sent_,state.data(),4096));
assert(batch.bytes[0]==0x9e && batch.bytes[2]==0x9e);
}}
'''
with tempfile.TemporaryDirectory() as td:
 f=Path(td)/'test.cpp';f.write_text(c);sp.run(['c++','-std=c++17','-O2',f,'-o',f.with_suffix('')],check=True);sp.run([f.with_suffix('')],check=True)
print('32768 masks matched producer shadow, consumer state, subsequent ordinary delta offset')
