// Aggregate real, consecutive taken transfers between mapped PCs in the
// training frames only. Ignore exits to unobserved code and straight falls.
#include <cstdint>
#include <cstdio>
#include <unordered_map>
struct Block{uint64_t pc;uint32_t bytes,frame;};
int main(int argc,char**argv){
 if(argc!=3)return 1;
 FILE*f=fopen(argv[1],"rb"),*o=fopen(argv[2],"w");if(!f||!o)return 2;
 uint64_t h[4];if(fread(h,8,4,f)!=4||h[0]!=0x4e4742434f444531ull)return 3;
 std::unordered_map<uint64_t,uint64_t> counts;Block buf[8192],prev{};uint64_t total=0;
 while(size_t n=fread(buf,sizeof(Block),8192,f)){total+=n;for(size_t i=0;i<n;i++){
   Block b=buf[i];
   if(b.frame<1802&&prev.frame==b.frame&&prev.bytes>=4&&prev.pc>=h[1]&&prev.pc+prev.bytes<=h[2]&&b.pc>=h[1]&&b.pc<h[2]&&prev.pc+prev.bytes!=b.pc){
    uint64_t a=prev.pc+prev.bytes-4-h[1],z=b.pc-h[1];if(a>UINT32_MAX||z>UINT32_MAX)return 4;
    counts[(a<<32)|z]++;
   }prev=b;
 }}
 if(total!=h[3])return 5;
 for(auto v:counts)fprintf(o,"%x %x %llu\n",unsigned(v.first>>32),unsigned(v.first),(unsigned long long)v.second);
 return fclose(o);
}
