from pathlib import Path
import tempfile,subprocess,runpy
body=runpy.run_path(str(Path(__file__).with_name('index-equal.py')))['body']
code='#include <arm_neon.h>\n#include <cstring>\n#include <vector>\n#include <cstdlib>\n'+body+r'''
int main(){std::vector<uint8_t> x(8224),y(8224);
for(unsigned size=128;size<=8192;size+=2){
 unsigned off=size%17,off2=size%13;auto a=x.data()+off,b=y.data()+off2;
 for(unsigned i=0;i<size;i++)a[i]=b[i]=uint8_t(i^size);
 if(!index_bytes_equal(a,b,size))abort();
 for(unsigned pos:{0u,15u,63u,64u,size/2,size-1}){b[pos]^=1;if(index_bytes_equal(a,b,size))abort();b[pos]^=1;}
}}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'check.cpp';f.write_text(code);out=f.with_suffix('')
 subprocess.run(['c++','-O2','-std=c++17',str(f),'-o',out],check=True);subprocess.run([out],check=True)
print('4033 eligible lengths; every equal case and six mismatch positions matched')
