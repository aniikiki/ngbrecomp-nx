"""Run the actual old/new extraction on mapped and fallback pages, including edges."""
from pathlib import Path
import subprocess,tempfile,runpy
here=Path(__file__).parent
s=Path('src/d3d/gpu/threaded.cpp').read_text()
new=runpy.run_path(str(here/'header-span.py'))['transform'](s)
def body(src):
 a=src.index('        HeaderCopy now{};');b=src.index('        Recent&',a);return src[a:b]+'return now;'
code=r'''
#include <cstdint>
#include <cstring>
#include <cstdlib>
#define NGB_DIRECT3D
static unsigned char raw[8200];static bool mapped;
static void* DirectPage(uint32_t v,size_t n){return mapped&&n<=4096-(v&4095)?raw+v:nullptr;}
namespace kernel{void* HostPtr(uint32_t v,size_t n=1){return raw+v;}uint32_t R32(uint32_t v){uint32_t x;std::memcpy(&x,HostPtr(v,4),4);return x;}}
struct HeaderCopy{uint32_t w[5];};
'''+ 'HeaderCopy orig(unsigned header){'+body(s)+'} HeaderCopy cand(unsigned header){'+body(new)+r'''}
int main(){for(unsigned i=0;i<sizeof raw;i++)raw[i]=i*33+7;
for(unsigned m=0;m<2;m++)for(unsigned t=0;t<8;t++)for(unsigned h=1;h<=4096;h++){
mapped=m;uint32_t x=0x80000000u|(t<<16);memcpy(raw+h,&x,4);auto a=orig(h),b=cand(h);if(memcmp(&a,&b,sizeof a))abort();}}
'''
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'test.cpp';f.write_text(code);o=f.with_suffix('')
 subprocess.run(['c++','-std=c++17','-O2',str(f),'-o',o],check=True);subprocess.run([o],check=True)
print('65536 resource-header extractions matched')
