"""Compile the actual recorder methods; compare delta headers, payload and sent state."""
from pathlib import Path
import os,runpy,subprocess,tempfile
s=Path('src/d3d/gpu/threaded.cpp').read_text()
s=runpy.run_path(str(Path(__file__).with_name('material-pieces.py')))['transform'](s)
body=s[s.index('    void WriteDelta('):s.index('    template<size_t... I>')].replace('#ifdef NGB_DIRECT3D','')
src='''
#include <algorithm>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>
bool material_control;
struct State { uint8_t untouched[4],material[68]; };
struct Range {size_t off,len;};
constexpr Range kStateRanges[]={{4,68}};
constexpr size_t kPiece=64;
struct Recorder {
State sent_{};
struct Batch {std::vector<uint8_t> bytes;} batch;
Batch *cur_=&batch;
'''+body+'''
};
int main(){
    Recorder a,b; State next{};
    for(unsigned head=0;head<=64;head++)
      for(unsigned tail=0;tail<=4;tail++){
        if(head<64) next.material[head]^=173;
        if(tail<4) next.material[64+tail]^=87;
        a.batch.bytes.clear();b.batch.bytes.clear();
        material_control=true;a.SendFixedRange<0>((const uint8_t*)&next);
        material_control=false;b.SendFixedRange<0>((const uint8_t*)&next);
        assert(a.batch.bytes==b.batch.bytes);
        assert(!memcmp(&a.sent_,&next,sizeof next)&&!memcmp(&b.sent_,&next,sizeof next));
      }
}
'''
with tempfile.TemporaryDirectory() as tmp:
    exe=Path(tmp)/'check'
    subprocess.run([os.getenv('CXX','c++'),'-std=c++17','-O2','-x','c++','-','-o',str(exe)],input=src,text=True,check=True)
    subprocess.run([exe],check=True)
print('325 material transitions: headers, payload and resulting state identical')
