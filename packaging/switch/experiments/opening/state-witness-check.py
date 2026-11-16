"""Differential test the actual changed template, range scanning and delta writes."""
from pathlib import Path
import tempfile,subprocess,runpy
p=Path(__file__).parent
s=Path('src/d3d/gpu/threaded.cpp').read_text();candidate=runpy.run_path(str(p/'state-witness.py'))['transform'](s)
def arm(t,name):
 a=t.index('    void WriteDelta(') if name=='A' else t.index('    size_t *active_witness_')
 b=t.index('    template<size_t... I>',a)
 return 'struct '+name+'{Batch store,*cur_=&store;uint8_t sent_[1792]={};'+t[a:b].replace('#ifdef NGB_DIRECT3D','')+'};'
code=r'''
#include <cstdint>
#include <cstring>
#include <vector>
#include <algorithm>
#include <array>
#include <cstdlib>
using std::size_t;
struct Batch{std::vector<uint8_t> bytes;};struct Range{size_t off,len;};
constexpr std::array<Range,4> kStateRanges={{{5,1336},{1345,128},{1473,227},{1700,16}}};constexpr size_t kPiece=64;
'''+arm(s,'A')+arm(candidate,'B')+r'''
int main(){A a;B b;uint8_t now[1792]={};uint32_t x=2673;
for(unsigned n=0;n<50000;n++){x=1664525*x+1013904223;
for(unsigned j=0;j<(n%8);j++){x=x*1664525+1013904223;now[x%1792]^=1+(x%255);}if(n%3)now[683]^=7;
a.store.bytes.clear();b.store.bytes.clear();
#define MATCH(i) a.SendFixedRange<i>(now);b.SendFixedRange<i>(now)
MATCH(0);MATCH(1);MATCH(2);MATCH(3);
if(a.store.bytes!=b.store.bytes||memcmp(a.sent_,b.sent_,1792))abort();}}
'''
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'test.cpp';f.write_text(code);out=f.with_suffix('')
 subprocess.run(['c++','-O2','-std=c++17',str(f),'-o',out],check=True);subprocess.run([out],check=True)
print('50000 four-range updates matched byte-for-byte')
