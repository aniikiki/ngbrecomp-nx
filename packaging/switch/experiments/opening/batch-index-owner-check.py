"""Replay actual ownership code across collisions, mutation and delayed consumption."""
from pathlib import Path
import runpy,tempfile,subprocess
p=Path(__file__).parent
s=Path('src/d3d/gpu/threaded.cpp').read_text()
s=runpy.run_path(str(p/'batch-index-owner.py'))['transform'](s)
types=s[s.index('struct IndexSnapshot {'):s.index('#endif',s.index('struct IndexSnapshot {'))]
a=s.index('    IndexSlot* CaptureIndices(')
capture=s[a:s.index('\n    }',a)+6]
a=s.index('            auto snapshot = CaptureIndices');b=s.index(' else\n#endif',a)
draw=s[a:b]
code='''
#include <vector>
#include <memory>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
struct IndexBounds{unsigned lo,hi;};
IndexBounds IndexRange(const uint8_t*,unsigned){return {};}
'''+types+'''
struct B {std::vector<std::shared_ptr<const IndexSnapshot>> index_snapshots;
 uint64_t id; std::vector<std::pair<unsigned,std::vector<uint8_t>>> expect;};
struct Trial{IndexSlot index_slots_[2048]{};B*cur_;unsigned index_hits_=0;
'''+capture+'''
void record(const uint8_t* indices,unsigned count){struct{int d;unsigned size;}c{};
'''+draw+'''
 if(c.d==2)cur_->expect.emplace_back(c.size,std::vector<uint8_t>(indices,indices+count*2));}
};
int main(){Trial t;std::vector<uint8_t> ram(65536);std::array<B,3> q{};
 unsigned recorded=0,owners=0;auto check=[&](B&b){
 for(auto& row:b.expect)assert(row.second==b.index_snapshots.at(row.first)->bytes);
 recorded+=b.expect.size();owners+=b.index_snapshots.size();b.expect.clear();b.index_snapshots.clear();};
 for(int i=1;i<=900;++i){auto &b=q[i%3];check(b);b.id=i;t.cur_=&b;
 for(unsigned j=0;j<160;++j){unsigned slot=(j/8+i)%9,n=j%47?64+slot:31;
 auto*src=ram.data()+slot*2048;if(j%13==0)src[i%(2*n)]++;
 t.record(src,n);}}
 for(auto&b:q)check(b);assert(recorded>50000 && owners<recorded/2);}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'x.cpp';f.write_text(code)
 subprocess.run(['c++','-std=c++17','-O2',f,'-o',f.with_suffix('')],check=True)
 subprocess.run([f.with_suffix('')],check=True)
print('144000 submissions with delayed consumption passed')
