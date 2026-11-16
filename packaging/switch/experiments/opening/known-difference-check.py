"""Execute both actual SendRange bodies; compare ordered writes and final state."""
from pathlib import Path
import runpy,subprocess,tempfile
d=Path(__file__).resolve().parent;s=(d.parents[3]/'src/d3d/gpu/threaded.cpp').read_text()
t=runpy.run_path(str(d/'known-difference.py'))['transform'](s)
code='''#include <algorithm>
#include <array>
#include <cstring>
#include <vector>
#include <cstdint>
#include <cassert>
#include <utility>
struct Range{size_t off,len;}; constexpr size_t kPiece=64;
'''
def klass(name,src):
    a=src.index('    void SendRange(');b=src.index('\n    }',a)+6
    return 'struct '+name+'''{std::array<uint8_t,1024> sent_{};
    std::vector<std::pair<size_t,size_t>> writes;
    void WriteDelta(size_t i,const uint8_t*n,size_t k){writes.emplace_back(i,k);std::memcpy(sent_.data()+i,n+i,k);}
'''+src[a:b]+'};\n'
code+=klass('Ref',s)+klass('Test',t)+'''int main(){for(unsigned len=1;len<=773;++len)for(unsigned mode=0;mode<30;++mode){
Ref a;Test b;auto src=a.sent_;size_t off=7;
for(unsigned i=0;i<len;i++)if(mode==1|| (mode==2 && i==len-1)||(mode==3 && i==0)||(mode>=4 && ((i/64+mode)%7==0 || (i*19+mode*71)%199==0)))src[off+i]=215;
bool diff=memcmp(src.data()+off,a.sent_.data()+off,len)!=0;
for(bool fixed:{false,true}){a=Ref{};b=Test{};if(!fixed||diff){a.SendRange(src.data(),{off,len});b.SendRange(src.data(),{off,len},fixed);}
assert(a.sent_==b.sent_ && a.writes==b.writes);}
}}'''
with tempfile.TemporaryDirectory() as tmp:
    f=Path(tmp)/'t.cpp';f.write_text(code);exe=f.with_suffix('')
    subprocess.run(['c++','-std=c++17','-O2',str(f),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print('46380 range updates matched')
