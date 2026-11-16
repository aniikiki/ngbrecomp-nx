"""Run both actual parsers on identical packets; include nested Draw which re-enters the parser."""
from pathlib import Path
import runpy,tempfile,subprocess,sys
p=Path(__file__).parent;s=Path('src/d3d/hle.cpp').read_text()
def body(t):
 a=t.index('void RunPushBuffer(uint32_t pb) {');return t[a:t.index('\n}',a)+2]
c='''
#include <vector>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
static uint32_t mem[1<<18];
static void *HostPtr(uint32_t a){return &mem[(a&0x7fffffffu)/4];}
static uint32_t R32(uint32_t a){return *(uint32_t*)HostPtr(a);}
static std::vector<uint32_t> seen;static void (*parse)(uint32_t);static bool nesting;
static void Draw(uint32_t prim,uint32_t start,uint32_t n,const uint8_t* p){
 seen.push_back(prim);seen.push_back(n);seen.push_back(p!=nullptr);
 if(!nesting){nesting=true;parse(16);nesting=false;}
 for(uint32_t i=0;i<n;i++){uint16_t w;memcpy(&w,p+2*i,2);seen.push_back(w);}
}
'''
variant=runpy.run_path(str(p/('push-overwrite.py' if '--overwrite' in sys.argv else 'push-scratch.py')))
c+=variant.get('allocator','')
c+=body(s).replace('void RunPushBuffer','void ref')+'\n'+body(variant['transform'](s)).replace('void RunPushBuffer','void alt')
c+='''
int main(){unsigned seed=123;auto rand32=[&]{return seed=seed*1664525+1013904223;};
 mem[5]=0x100;mem[7]=20;unsigned j=0x100/4;mem[j++]=(1<<18)|0x17fc;mem[j++]=3;mem[j++]=(2<<18)|0x1800;mem[j++]=1;mem[j++]=2;
 for(unsigned r=0;r<3000;r++){unsigned i=0x1000/4;mem[1]=0x1000;
 for(unsigned k=0;k<50;k++){unsigned op=rand32()%6;if(op==0 || op==1 || !k){mem[i++]=(1<<18)|0x17fc;mem[i++]=op?3:0;}
 else{unsigned n=r%13==0 ? 2047 : (rand32()>>17)%12;mem[i++]=(n<<18)|(op&1?0x1808:0x1800);for(unsigned z=0;z<n;z++)mem[i++]=rand32();}}
 mem[3]=4*i-0x1000;seen.clear();parse=ref;parse(0);auto expected=seen;seen.clear();parse=alt;parse(0);if(seen!=expected)abort();}
 puts("3000 packet streams matched including nested calls and oversized buffers");}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'check.cpp';f.write_text(c);exe=f.with_suffix('');subprocess.run(['c++','-std=c++17','-O2',f,'-o',exe],check=True);subprocess.run([exe],check=True)
