"""Decode the actual seed, generate each fixed VS, and compare both palette builders."""
from pathlib import Path
import runpy,struct,subprocess,tempfile
p=Path(__file__).resolve().parent
d=Path('build/switch-runtime/core-perf/opening-present-combined')
src=Path('src/d3d/vk/backend.cpp').read_text()
new=runpy.run_path(str(p/'blend-palette.py'))['transform'](src)
def block(s):
    a=s.index('        if (fk.blend) {');return s[a:s.index('            float pvm[16];',a)]+'}}'
lib=src[src.index('void InverseTranspose3x3('):src.index('#include "spark_aspect.h"')]
pre='''
#include "gpu/shaders.h"
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <regex>
using namespace gpu;
struct S {std::array<std::array<float,16>,260> transforms{};};
'''
sig='(const FixedKey& fk, const S& s, DrawConstants& c){'
main=r"""
int main(int argc,char** argv){
 FILE* f=fopen(argv[1],"rb");assert(f);unsigned char r[39];unsigned keys=0,blend=0;
 while(fread(r,1,39,f)==39){
    uint16_t regs;uint64_t decode;FixedKey fk;
    memcpy(&regs,r,2);memcpy(&decode,r+3,8);memcpy(&fk,r+11,sizeof fk); keys++;
    auto text=FixedVertexHlsl(regs,r[2],decode,fk);
    if(!fk.blend)continue;
    assert(!r[2] && fk.blend==1);blend++;
    for(auto name:{"wvb","wvbn"}){
        std::regex ref(std::string(name)+R"(\[([^\]]+)\])");
        unsigned mask=0;
        for(std::sregex_iterator i(text.begin(),text.end(),ref),end;i!=end;++i){
            auto v=(*i)[1].str();
            if(v=="4"){assert(text.substr(i->position()+i->length(),1)==";");continue;}
            assert(v=="0"||v=="1");mask|=1u<<(v=="1");
        }assert(mask==3);
    }
 } fclose(f);
 FILE* t=fopen(argv[2],"rb");assert(t);unsigned char rec[216];int n=0;
 FixedKey fk{};fk.blend=1; S s{};
 while(fread(rec,1,sizeof rec,t)==sizeof rec){
    memcpy(s.transforms[256].data(),rec+24,64);
    memcpy(s.transforms[2].data(),rec+88,64);
    // Slot 1 is a fixture (actual slot 1 not captured); recompute it in both.
    memcpy(s.transforms[257].data(),rec+152,64);
    DrawConstants a{},b{};float w[16],nm[16]{};
    MatMul(s.transforms[256].data(),s.transforms[2].data(),w);
    Transpose(w,a.wv);InverseTranspose3x3(w,nm);Transpose(nm,a.wvn);b=a;
    oldpath(fk,s,a);newpath(fk,s,b);
    assert(!memcmp(a.wvb,b.wvb,128)&&!memcmp(a.wvbn,b.wvbn,128));n++;
 } fclose(t);assert(n>0);std::cout<<keys<<" fixed keys, "<<blend<<" blended keys, "<<n<<" matrix fixtures\n";
}
"""
with tempfile.TemporaryDirectory() as tmp:
    t=Path(tmp);cpp=t/'check.cpp';exe=t/'check'
    cpp.write_text(pre+lib+'void oldpath'+sig+block(src)+'\nvoid newpath'+sig+block(new)+main)
    subprocess.run(['c++','-std=c++20','-O2','-Isrc/d3d',cpp,'src/d3d/gpu/shaders.cpp','-o',exe],check=True)
    for frames in (30,120):
        seed=(d/f'opening-{frames}.recipes').read_bytes();assert seed[:8]==b'NGBD3DC1'
        keys=bytearray();i=8
        while i<len(seed):
            k,_,n=struct.unpack_from('<cQI',seed,i);i+=13
            if k==b'F':assert n==39;keys.extend(seed[i:i+n])
            i+=n
        assert i==len(seed)
        f=t/'keys';f.write_bytes(keys)
        path=Path('build/switch-runtime/core-perf/opening-clip-join/producer.bin')
        assert path.stat().st_size%216==0
        subprocess.run([exe,f,path],check=True)
