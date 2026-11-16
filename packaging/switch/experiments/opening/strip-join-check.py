"""Exercise extracted C++ join code on inline storage and immutable queued snapshots."""
from pathlib import Path
import tempfile,subprocess,runpy
p=Path(__file__).resolve().parent
s=runpy.run_path(str(p/'strip-snapshot-join.py'))['transform'](Path('src/d3d/gpu/threaded.cpp').read_text())
j=s[s.index('    bool TryJoinStrips('):s.index('\n#endif',s.index('    bool TryJoinStrips('))]
prefix=r'''
#include <vector>
#include <array>
#include <memory>
#include <cstring>
#include <algorithm>
#include <cstdint>
#include <cassert>
#include <cstdlib>
enum {kRsZEnable,kRsFillMode};
struct State {int rs[2]={1,0}; unsigned vs_handle=0;unsigned textures[4]={};struct {unsigned data;}rt{},zs{};};
namespace kernel {unsigned R32(unsigned){return 0;}}
struct Cmd {unsigned data=0,c=0,d=0,size=0;};
struct Snap {std::vector<uint8_t> bytes;};struct Batch {std::vector<uint8_t> bytes;std::vector<std::shared_ptr<const Snap>> index_snapshots;};
struct Test {Batch obj,*cur_=&obj;bool recording_visibility_=false;
unsigned Put(const void*p,size_t n){size_t a=(obj.bytes.size()+3)&~size_t(3);obj.bytes.resize(a+n);memcpy(obj.bytes.data()+a,p,n);return a;}
'''
tail=r'''
};
using Tri=std::array<unsigned,3>;
std::vector<Tri> tris(const uint16_t* p,unsigned n){
 std::vector<Tri> v;for(unsigned i=2;i<n;i++){auto a=p[i-2],b=p[i-1],c=p[i];if(a==b||b==c||a==c)continue;
 if(i&1)std::swap(a,b);v.push_back({a,b,c});}return v;
}
int main(){for(unsigned a:{3u,4u,31u,32u,63u,64u,65u,511u,4096u})for(unsigned b:{3u,4u,33u,64u,511u,4096u})for(unsigned mode:{1u,2u}){
 Test t;State st;Cmd prev;std::vector<uint16_t> x(a),y(b);for(unsigned i=0;i<a;i++)x[i]=(i*3)%17;for(unsigned i=0;i<b;i++)y[i]=(i*5+1)%17;
 auto snap=std::make_shared<Snap>();snap->bytes.resize(a*2);memcpy(snap->bytes.data(),x.data(),a*2);
 prev.d=mode;prev.c=a;t.obj.bytes.resize(12,0xa5);if(mode==2)t.obj.index_snapshots.push_back(snap);else prev.data=t.Put(x.data(),a*2);
 auto exp=tris(x.data(),a),z=tris(y.data(),b);exp.insert(exp.end(),z.begin(),z.end());
 assert(t.TryJoinStrips(st,prev,(uint8_t*)y.data(),b));assert(prev.d==1&&prev.c==a+b+2+(a&1));
 std::vector<uint16_t> out(prev.c);memcpy(out.data(),t.obj.bytes.data()+prev.data,2*prev.c);assert(exp==tris(out.data(),prev.c));
 assert(!memcmp(snap->bytes.data(),x.data(),2*a));for(unsigned k=0;k<12;k++)assert(t.obj.bytes[k]==0xa5);
}}
'''
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'check.cpp';f.write_text(prefix+j+tail)
 subprocess.run(['c++','-std=c++17','-O2',str(f),'-o',t+'/test'],check=True)
 subprocess.run([t+'/test'],check=True)
print('108 accepted cases: triangle order and winding, packet offset and snapshot bytes match')
