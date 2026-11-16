"""Differential check the actual delta writer calls and sent-state bytes."""
from pathlib import Path
import subprocess,tempfile
p=Path(__file__).resolve().parent
src=(p.parents[3]/'src/d3d/gpu/threaded.cpp').read_text()
orig=src[src.index('    void SendRange('):src.index('#ifdef NGB_DIRECT3D',src.index('    void SendRange('))]
sizes=[1,63,64,65,127,128,129,192,193,255,256,257,511,512,513,1336]
c='''
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <vector>
#include <type_traits>
#include <cassert>
struct Range{size_t off,len;};
constexpr size_t kPiece=64;
constexpr Range kStateRanges[]={'''+','.join(f'{{7,{n}}}' for n in sizes)+'''};
struct Recorder{
 uint8_t sent_[1360]={};std::vector<std::pair<size_t,size_t>> calls;
 void WriteDelta(size_t off,const uint8_t*now,size_t n){calls.emplace_back(off,n);std::memcpy(sent_+off,now+off,n);}
'''+orig+(p/'fixed-pieces.inc').read_text()+'''
};
template<unsigned I> void check(){
 constexpr auto r=kStateRanges[I]; uint32_t x=12345;
 for(unsigned trial=0;trial<640;trial++){
 Recorder a,b;uint8_t now[1360];
 for(size_t j=0;j<sizeof now;j++){x=x*1664525u+1013904223u;a.sent_[j]=b.sent_[j]=now[j]=x>>24;}
 for(size_t j=0;j<r.len;j++){x=x*1664525u+1013904223u;
 bool change= trial<256 ? (trial&(1u<<(j/64%8)))!=0 : ((x>>24)<(trial%255));
 if(change)now[r.off+j]^=127;}
 if(std::memcmp(a.sent_+r.off,now+r.off,r.len)){
 a.SendRange(now,r);b.ChangedFixedRange<I>(now);
 }
 assert(a.calls==b.calls && !std::memcmp(a.sent_,b.sent_,sizeof a.sent_));
 }}
int main(){'''+''.join(f'check<{i}>();' for i in range(len(sizes)))+'}'
with tempfile.TemporaryDirectory() as temp:
 f=Path(temp)/'check.cpp';o=f.with_suffix('');f.write_text(c)
 subprocess.run(['c++','-std=c++17','-O2',str(f),'-o',str(o)],check=True);subprocess.run([str(o)],check=True)
print(len(sizes)*640,'matching command sequences and state snapshots')
