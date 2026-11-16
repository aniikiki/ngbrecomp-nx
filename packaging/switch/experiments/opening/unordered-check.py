import tempfile,runpy,subprocess
from pathlib import Path
d=Path(__file__).parent
transform=runpy.run_path(str(d/'unordered-branch.py'))['transform']
fns=''
for i,rel in enumerate(('<','<=','>','>=')):
    original=f'(_fca {rel} _fcb || (_fca != _fca || _fcb != _fcb))'
    alt,n=transform(original);assert n==1
    for label,v in [('ref',original),('alt',alt)]:
        fns+=f'__attribute__((noinline)) int {label}{i}(double _fca,double _fcb){{return {v};}}\n'
c='#include <stdint.h>\n#include <string.h>\n#include <assert.h>\n'+fns+'''
int main(){uint64_t edges[]={0,1,0x8000000000000000ULL,0x8000000000000001ULL,0x3ff0000000000000ULL,0xbff0000000000000ULL,0x7ff0000000000000ULL,0xfff0000000000000ULL,0x7ff8000000000001ULL,0x7ff0000000000001ULL,0x0010000000000000ULL,0x7fefffffffffffffULL};
 uint64_t x=19;
 for(int i=0;i<250000;++i){x=x*6364136223846793005ULL+1;uint64_t a=i%3?edges[i%12]:x;
 x=x*6364136223846793005ULL+1;uint64_t b=i%5?edges[(i/12)%12]:x;
 double p,q;memcpy(&p,&a,8);memcpy(&q,&b,8);
'''+''.join(f' assert(ref{i}(p,q)==alt{i}(p,q));\n' for i in range(4))+'}}'
with tempfile.TemporaryDirectory() as t:
 f=Path(t)/'x.c';f.write_text(c)
 subprocess.run(['cc','-O2','-fno-fast-math',f,'-o',f.with_suffix('')],check=True)
 subprocess.run([f.with_suffix('')],check=True)
print('1000000 branch outcomes matched')
