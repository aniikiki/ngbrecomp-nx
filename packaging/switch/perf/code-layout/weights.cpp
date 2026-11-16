#include <cstdint>
#include <cstdio>
#include <unordered_map>
#include <vector>
struct Block{uint64_t pc;uint32_t bytes,frame;};
int main(int argc,char**argv){
 if(argc!=3)return 1;
 FILE*f=fopen(argv[1],"rb"),*o=fopen(argv[2],"w");if(!f||!o)return 2;
 uint64_t h[4];if(fread(h,8,4,f)!=4||h[0]!=0x4e4742434f444531ull)return 3;
 std::unordered_map<uint64_t,uint64_t> hist;
 std::vector<Block> buf(16384);uint64_t n=0;
 while(size_t k=fread(buf.data(),sizeof(Block),buf.size(),f)){
  n+=k;for(size_t i=0;i<k;i++){auto b=buf[i];if(b.frame<1802||b.pc<h[1]||b.pc>=h[2])continue;
   if(b.pc-h[1]>UINT32_MAX)return 4;
   hist[((b.pc-h[1])<<32)|b.bytes]++;}
 }
 if(n!=h[3])return 5;
 for(auto v:hist)fprintf(o,"%x %x %llu\n",unsigned(v.first>>32),unsigned(v.first),(unsigned long long)v.second);
 return fclose(o);
}
