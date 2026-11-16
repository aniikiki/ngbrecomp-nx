from pathlib import Path
import runpy,tempfile,subprocess
p=Path(__file__).parent
s=Path('src/d3d/gpu/threaded.cpp').read_text()
def arm(src,n,alt):
 a=src.index('    void WriteDelta');b=src.index('\n    }',a)+6
 return ('struct '+n+'{ struct Batch{std::vector<uint8_t> bytes;};Batch buf,*cur_=&buf; uint8_t sent_[512]{};'+
 ('size_t delta_header_=0,delta_end_=0;' if alt else '')+src[a:b]+' void start(){'+('delta_end_=0;' if alt else '')+'}};')
t=runpy.run_path(str(p/'delta-adjacent.py'))['transform'](s)
code='''#include <vector>
#include <cstdint>
#include <cstring>
#include <cassert>
using std::size_t;
'''+arm(s,'A',False)+arm(t,'B',True)+'''
void apply(const std::vector<uint8_t>& v,size_t start,uint8_t* dst){while(start<v.size()){
uint32_t h[2];assert(v.size()-start>=8);memcpy(h,v.data()+start,8);start+=8;
assert(h[1] && h[0]+h[1]<=512 && h[1]<=v.size()-start);
memcpy(dst+h[0],v.data()+start,h[1]);start+=h[1];}}
int main(){ A a;B b;uint8_t now[512],x[512]{},y[512]{};uint32_t seed=91;
for(unsigned j=0;j<30000;j++){if(j%7==0){a.buf.bytes.clear();b.buf.bytes.clear();}
size_t sa=a.buf.bytes.size(),sb=b.buf.bytes.size(); a.start();b.start();
unsigned off=j%127;for(unsigned k=0;k<j%14;k++){seed=seed*1664525+1013904223;
unsigned n=1+(seed>>24)%46;if(off+n>512)off=0;memset(now,seed>>8,sizeof now);
a.WriteDelta(off,now,n);b.WriteDelta(off,now,n);off+=n;if(seed&1)off=(seed>>14)%400;}
apply(a.buf.bytes,sa,x);apply(b.buf.bytes,sb,y);
assert(!memcmp(x,y,512)&&!memcmp(a.sent_,b.sent_,512)&&!memcmp(y,b.sent_,512));}}
'''
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'t.cpp';f.write_text(code);exe=f.with_suffix('')
 subprocess.run(['c++','-std=c++17','-O2',str(f),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print('30000 State commands matched after decode and shadow update')
