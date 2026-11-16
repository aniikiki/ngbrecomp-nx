"""Exercise the actual vector mask, including mismatches at the last accessible byte."""
import tempfile,subprocess,runpy
from pathlib import Path
p=Path(__file__).parent
snip=runpy.run_path(str(p/'four-piece.py'))['transform']((Path('src/d3d/gpu/threaded.cpp')).read_text())
header=snip[:snip.index((Path('src/d3d/gpu/threaded.cpp')).read_text()[:48])]
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'check.cpp';f.write_text(header+'''
#include <sys/mman.h>
#include <unistd.h>
#include <cstring>
int main(){
 size_t page=sysconf(_SC_PAGESIZE);
 auto buf=[&](){auto p=(unsigned char*)mmap(0,page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 if(p==MAP_FAILED||mprotect(p+page,page,PROT_NONE))std::abort();return p+page-256;};
 auto a=buf(),b=buf();unsigned cases=0;
 for(int off=0;off<16;off++)for(unsigned m=0;m<16;m++)for(int pos=0;pos<64;pos++){
    auto x=a-off,y=b-(15-off);
    std::memset(x,137,256);std::memset(y,137,256);
    for(int j=0;j<4;j++)if(m&(1<<j))y[64*j+(pos+j*17)%64]^=1+(j*41);
    if(four_piece_mask(x,y)!=m)std::abort();++cases;
 }
 std::printf("%u vector masks matched\\n",cases);
}
''')
 exe=Path(t)/'check';subprocess.run(['g++','-O2','-mcpu=cortex-a57',f,'-o',exe],check=True);subprocess.run([exe],check=True)
