"""Differential test of generated header flush/reader across reused batches."""
from pathlib import Path
import subprocess,tempfile,runpy
p=Path(__file__).resolve().parent
s=Path('src/d3d/gpu/threaded.cpp').read_text()
t=runpy.run_path(str(p/'batch-headers.py'))['transform'](s)
def block(s,start):return s[s.index(start):s.index('\n    }',s.index(start))+6]
def emit(s,new):
    flush=block(s,'    void FlushHeaders()')
    read=s[s.index('                for (uint32_t i = 0; i < c.size; i++)'):s.index('                    HeaderCopy& to')]
    push=s.split('std::memcpy(h.w, now.w, sizeof h.w);\n')[1].split(';')[0]+';'
    return ('struct '+('B' if new else 'A')+'{struct Batch{std::vector<Cmd> cmds; std::vector<uint8_t> bytes;'
        +('std::vector<HeaderSend> header_records;size_t header_first=0;' if new else '')+
        '};Batch pool[3],*cur_=pool;std::vector<HeaderSend> pending_headers_;'
        +block(s,'    uint32_t Put(')+flush+' void push(HeaderSend h){'+push+'} table process(unsigned slot){Batch& b=pool[slot];table out;'
        +'for(const Cmd& c:b.cmds){ const auto* data=b.bytes.data()+c.data;'+read+
        'out.emplace_back(h.addr,h.w[0],h.w[4],h.data>=0?int(b.bytes.at(h.data)):-1);}out.emplace_back(0,0,0,-2);}'+
        ('b.header_records.clear();b.header_first=0;' if new else '')+'b.bytes.clear();b.cmds.clear();return out;}};')
code='#include <vector>\n#include <tuple>\n#include <cstring>\n#include <cstdint>\n#include <cstdlib>\nusing std::size_t;using table=std::vector<std::tuple<unsigned,unsigned,unsigned,int>>;enum class Op{Headers};struct Cmd{Op op;uint32_t a=0,data=0,size=0;};'+s[s.index('struct HeaderSend {'):s.index('\n};',s.index('struct HeaderSend {'))+3]+emit(s,False)+emit(t,True)+'''
int main(){A a;B b;unsigned seed=47;
for(unsigned turn=0;turn<3000;turn++){unsigned slot=turn%3;
if(a.process(slot)!=b.process(slot))abort();a.cur_=&a.pool[slot];b.cur_=&b.pool[slot];
for(unsigned j=0;j<39;j++){seed=1664525*seed+1013904223;
HeaderSend x{seed%23+1,{seed,j,slot,turn,~seed}},y=x;if(seed&2){
x.data=a.Put(&seed,3);y.data=b.Put(&seed,3);}
a.push(x);b.push(y);if(seed&8){a.FlushHeaders();b.FlushHeaders();}}
a.FlushHeaders();b.FlushHeaders();a.FlushHeaders();b.FlushHeaders();}
for(unsigned i=0;i<3;i++)if(a.process(i)!=b.process(i))abort();}
'''
with tempfile.TemporaryDirectory() as d:
    f=Path(d)/'test.cpp';f.write_text(code);exe=f.with_suffix('')
    subprocess.run(['c++','-std=c++17','-O2',str(f),'-o',exe],check=True)
    subprocess.run([exe],check=True)
print('117000 header sends, including inline payloads and delayed batch reads, matched')
