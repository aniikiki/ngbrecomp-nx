"""Delay consumption across overwrites/cache replacements and share multiple batches."""
from pathlib import Path
import tempfile, subprocess,runpy
d=Path(__file__).parent
src=runpy.run_path(str(d/'consumer-bounds.py'))['transform'](Path('src/d3d/gpu/threaded.cpp').read_text())
a=src.index('struct IndexSnapshot {');b=src.index('struct IndexSlot',a)
v=Path('src/d3d/gpu/vertex.cpp').read_text();i=v.index('IndexBounds IndexRange(');j=v.index('\n}',i)+2
code="""
#include <algorithm>
#include <cassert>
#include <vector>
#include <memory>
#include <cstring>
#include <cstdint>
using std::size_t;
struct IndexBounds { uint32_t first,last; };
static unsigned scans;
"""+v[i:j].replace('uint16_t lo16','++scans; uint16_t lo16')+src[a:b]+"""
int main(){
 std::vector<uint8_t> buf(8192);
 std::vector<std::shared_ptr<const IndexSnapshot>> batch;
 std::vector<IndexBounds> expected;
 for(unsigned n=64;n<=4096;++n){
  for(unsigned k=0;k<2*n;++k)buf[k]=(k*79+n*51+(k>>3))&255;
  auto p=std::make_shared<IndexSnapshot>();p->bytes.assign(buf.begin(),buf.begin()+2*n);
  expected.push_back(IndexRange(buf.data(),n));batch.push_back(p);batch.push_back(p);
 }
 scans=0;
 for(size_t i=batch.size();i>0;){
  --i;auto b=batch[i]->Bounds();assert(b->first==expected[i/2].first && b->last==expected[i/2].last);
 }
 assert(scans==expected.size());
}
"""
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'x.cpp').write_text(code)
 subprocess.run(['c++','-std=c++17','-O2',p/'x.cpp','-o',p/'x'],check=True)
 subprocess.run([p/'x'],check=True)
print('4033 snapshot lengths; 8066 delayed draws verified')
