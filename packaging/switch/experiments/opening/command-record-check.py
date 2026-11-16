"""Run original and changed record/decode statements on identical commands.
Mutate source surfaces after recording; reuse batches between rounds."""
from pathlib import Path
import runpy,tempfile,subprocess
p=Path(__file__).resolve().parent
orig=(p.parents[3]/'src/d3d/gpu/threaded.cpp').read_text()
alt=runpy.run_path(str(p/'command-record.py'))['transform'](orig)
def cut(s,a,b):
 i=s.index(a);return s[i:s.index(b,i)]
def harness(s,new):
 cmd=cut(s,'enum class Op','// a header copy')
 copy=cut(s,'        Cmd c{Op::Copy};','        if (!thread_) Submit();')
 pres=cut(s,'            Cmd c{Op::Present};','            id = Submit();').replace('inner_->CaptureQuick(cur_->quick.back());','cur_->quick.back()=seed;')
 state=cut(s,'        if (s.vs.get() != sent_.vs.get())','    // the batch handed over')
 play=cut(s,'            case Op::Copy:', '            case Op::Flush:').replace('inner_->','sink.')
 shaders=cut(s,'                if '+('(' if new else '(c.vs >= 0)'), '                break;') if not new else cut(s,'                if(c.a) state_.vs','                break;')
 return cmd+'''
 struct B{std::vector<Cmd>cmds;std::vector<Surface>surfaces;std::vector<int>quick;
 std::vector<uint8_t>bytes;std::vector<std::shared_ptr<int>>vs,ps;};
 struct Test{B b; B*cur_=&b; State sent_,state_;Sink sink;std::vector<Surface> input;
 unsigned Put(const uint8_t*p,size_t n){unsigned off=b.bytes.size();b.bytes.insert(b.bytes.end(),p,p+n);return off;}
 void record(State s,size_t first){Cmd c{Op::State};
'''+state+'''void copy(Surface src,Surface dst,uint32_t count,const uint8_t*src_rects,const uint8_t*dst_points){
'''+copy+'''}void present(Surface front,int seed){
'''+pres+'''}void run(){for(auto c:b.cmds)switch(c.op){case Op::State:
'''+shaders+'''sink.shader(state_);break;
'''+play+'''default:abort();}b=B{};} };'''
src='''
#include <vector>
#include <cstdint>
#include <memory>
#include <cassert>
#include <cstdlib>
struct Surface{unsigned a,b,c,d;};struct State{std::shared_ptr<int>vs,ps;};
struct Sink{std::vector<unsigned> v;
void surf(Surface s){v.insert(v.end(),{s.a,s.b,s.c,s.d});}
void Copy(Surface a,Surface b,unsigned n,const unsigned char*r,const unsigned char*p){surf(a);surf(b);v.push_back(n);for(unsigned i=0;r&&i<n*16;i++)v.push_back(r[i]);for(unsigned i=0;p&&i<n*8;i++)v.push_back(p[i]);}
void UseQuick(int i){v.push_back(i);}void Present(Surface s){surf(s);}
void shader(State s){v.push_back(s.vs?*s.vs:0);v.push_back(s.ps?*s.ps:0);} };
'''+''.join('namespace '+k+'{'+harness(s,new)+'}' for k,s,new in [('ref',orig,False),('alt',alt,True)])+'''
static_assert(sizeof(ref::Cmd)==76&&sizeof(alt::Cmd)==32);
int main(){ref::Test a;alt::Test b;std::shared_ptr<int> sp[7]={};for(int i=1;i<7;i++)sp[i]=std::make_shared<int>(i);
for(unsigned round=0;round<5;round++){for(unsigned i=0;i<400;i++){Surface x{i,12,i*3,round},y{5,i,3,i+round};
unsigned char data[48];for(unsigned j=0;j<48;j++)data[j]=j+i;
for(auto test:[&]{return std::vector<int>{0,1};}()){
#define RECORD(t) t.copy(x,y,i%4,i%2?data:nullptr,i%3?data:nullptr);t.present(x,i);t.record({sp[i%7],sp[(i/5)%7]},t.b.bytes.size());
if(test){RECORD(b)}else{RECORD(a)}
}}
a.run();b.run();assert(a.sink.v==b.sink.v);}}
'''
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'check.cpp';exe=f.with_suffix('');f.write_text(src)
 subprocess.run(['c++','-std=c++17','-O2',str(f),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print('matched old/new backend arguments across 5 batches, 2000 mixed input sets')
