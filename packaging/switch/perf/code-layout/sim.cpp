// Replay actual AArch64 block ranges against section address maps.
// The caller selects only functions shared by the host runner and target ELF.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
struct Block{uint64_t pc;uint32_t size,frame;};
struct Fn{uint64_t pc,size;std::array<uint64_t,4> loc;};
struct Model{
    uint64_t il[256][3]{},pages[48]{},im=0,pm=0;
    void hit(uint64_t a,unsigned n){
        for(uint64_t l=a>>6;l<=(a+n-1)>>6;++l){
            auto *set=il[l%256];uint64_t v=l+1;
            if(set[0]==v)continue;
            if(set[1]!=v){if(set[2]!=v)im++;set[2]=set[1];}set[1]=set[0];set[0]=v;
        }
        for(uint64_t l=a>>12;l<=(a+n-1)>>12;++l){
            uint64_t v=l+1;if(pages[0]==v)continue;
            unsigned j=1;while(j<48 && pages[j]!=v)++j;
            if(j==48){pm++;j--;}for(;j;j--)pages[j]=pages[j-1];pages[0]=v;
        }
    }
};
int main(int argc,char **argv){
    if(argc!=3)return 1;
    std::ifstream in(argv[1]);unsigned m;if(!(in>>m)||m<1||m>4)return 2;
    std::vector<Fn> funcs;Fn f{};
    while(in>>f.pc>>f.size){for(unsigned j=0;j<m;j++)if(!(in>>f.loc[j]))return 3;funcs.push_back(f);}
    std::vector<Model> model(m);std::ifstream b(argv[2],std::ios::binary);uint64_t h[4];
    if(!b.read((char*)&h,sizeof h)||h[0]!=0x4e4742434f444531ull)return 4;
    std::vector<Block> chunk(8192);unsigned frame=0;
    struct Pos{int i;uint32_t off;};std::unordered_map<uint64_t,Pos> cache;
    auto dump=[&](){if(frame>=1802){std::cout<<"frame "<<frame<<" [I-line, 4KiB page] misses";for(auto& c:model)std::cout<<" ["<<c.im<<", "<<c.pm<<"]";std::cout<<"\n";}for(auto& c:model)c.im=c.pm=0;};
    for(uint64_t i=0;i<h[3];){
        size_t n=std::min<uint64_t>(h[3]-i,chunk.size());
        if(!b.read((char*)chunk.data(),n*sizeof(Block)))return 5;
        for(size_t j=0;j<n;j++){
            auto v=chunk[j];if(frame!=v.frame){dump();frame=v.frame;}
            if(v.pc<h[1]||v.pc>=h[2])continue;
            uint64_t pc=v.pc-h[1];auto it=cache.find(pc);
            if(it==cache.end()){
                auto t=std::upper_bound(funcs.begin(),funcs.end(),pc,[](uint64_t a,const Fn& f){return a<f.pc;});
                Pos p{-1,0};if(t!=funcs.begin()){--t;if(pc<t->pc+t->size)p={int(t-funcs.begin()),uint32_t(pc-t->pc)};}
                it=cache.emplace(pc,p).first;
            }
            auto pos=it->second;if(pos.i<0)continue;auto& f=funcs[pos.i];
            if(uint64_t(pos.off)+v.size>f.size)continue;
            for(unsigned k=0;k<m;k++)model[k].hit(f.loc[k]+pos.off,v.size);
        }i+=n;
    }dump();
}
