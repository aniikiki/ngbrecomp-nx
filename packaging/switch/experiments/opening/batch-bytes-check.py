"""Compare actual transformed Put, delta and strip writes against original batch bytes."""
from pathlib import Path
import tempfile,subprocess,runpy,re
p=Path(__file__).resolve().parent
orig=Path('src/d3d/gpu/threaded.cpp').read_text()
mod=runpy.run_path(str(p/'batch-bytes.py'));new=mod['transform'](orig)
def method(s,start):
    a=s.index(start);b=s.index('\n    }',a)
    return s[a:b+6]
def arm(s,vec,name):
    strip=s[s.index('        unsigned padding = 2 + (prev.c & 1);'):s.index('        prev.c += padding + count;')]
    return 'struct '+name+'{ struct Batch{'+vec+' bytes;}; Batch buf,*cur_=&buf; uint8_t sent_[512]={};'+method(s,'    uint32_t Put(')+method(s,'    void WriteDelta(')+' void strip(unsigned count,unsigned odd,const uint8_t* indices){size_t end=buf.bytes.size();struct {unsigned c;}prev{odd};'+strip+'}};'
code='#include <vector>\n#include <cstring>\n#include <cstdint>\n#include <cstdlib>\nusing std::size_t;\n'+mod['ARENA']+arm(orig,'std::vector<uint8_t>','A')+arm(new,'BatchBytes','B')+'''
int main(){A a; B b;unsigned rng=7267;uint8_t data[512];for(unsigned n=0;n<50000;n++){rng=rng*1664525+1013904223;
memset(data,rng>>24,sizeof data);size_t sz=(rng>>10)%400+1;
switch(rng%7){case 0:a.buf.bytes.clear();b.buf.bytes.clear();break;
case 1:case 2:a.WriteDelta(4,data,sz);b.WriteDelta(4,data,sz);break;
case 3:if(a.buf.bytes.size()>=2){a.strip(18,rng&1,data);b.strip(18,rng&1,data);}break;
default:if(a.Put(data,sz)!=b.Put(data,sz))abort();}
auto &x=a.buf.bytes;auto &y=b.buf.bytes;if(x.size()!=y.size()||(x.size()&&memcmp(x.data(),y.data(),x.size()))||memcmp(a.sent_,b.sent_,512))abort();}}
'''
with tempfile.TemporaryDirectory() as t:
    f=Path(t)/'test.cpp';f.write_text(code);out=f.with_suffix('')
    subprocess.run(['c++','-std=c++17','-O2',str(f),'-o',str(out)],check=True);subprocess.run([out],check=True)
print('50000 original vs recycled batch operations matched')
