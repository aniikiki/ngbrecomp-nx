// Standalone differential for the two experimental push decoders. Mutates the
// same guest address repeatedly, including the jump target and index words.
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <vector>
#include <cstdio>
static std::vector<uint32_t> input;
static std::vector<uint16_t> emitted,wanted;
static unsigned calls,primitive;
static const uint8_t* PushSpan(uint32_t,uint32_t){return (const uint8_t*)input.data();}
static void Draw(unsigned p,unsigned start,unsigned count,const uint8_t*src){
 if(start||++calls!=1)abort();primitive=p;emitted.resize(count);memcpy(emitted.data(),src,2*count);}
#include "fast.inc"
#include "span.inc"
static void reference(unsigned&draws,unsigned&prim){
 wanted.clear();unsigned active=0;
 for(unsigned i=0;i<input.size();){auto h=input[i++],c=(h>>18)&2047,m=h&0x1ffc;
 if((h&0xe0000003u)==0x20000000u||(h&3)==1)break;
 if(c>input.size()-i)abort();
 if(m==0x17fc){if(input[i]){active=input[i];wanted.clear();}else if(active){draws++;prim=active;active=0;}}
 if(m==0x1800)for(unsigned j=0;j<c;j++){wanted.push_back(input[i+j]);wanted.push_back(input[i+j]>>16);}
 if(m==0x1808)for(unsigned j=0;j<c;j++)wanted.push_back(input[i+j]);
 i+=c;}
 if(active&&!wanted.empty()){draws++;prim=active;}
}
int main(){uint32_t x=17;auto rnd=[&](){return x=x*1664525u+1013904223u;};
 unsigned admitted[2]={};for(unsigned k=0;k<50000;k++){
 if(k%3!=1){input={0x417fc,1+rnd()%10};for(unsigned j=0,n=1+rnd()%8;j<n;j++){
 unsigned cnt=1+rnd()%64,m=(rnd()>>20)%3?0x1800:0x1808;input.push_back(0x40000000u|(cnt<<18)|m);
 for(unsigned z=0;z<cnt;z++)input.push_back(rnd());}
 if(k%8<4){input.push_back(0x417fc);input.push_back(0);}
 if(k%8==5){input.push_back(0x417fc);input.push_back(2);input.push_back(0x41800);input.push_back(rnd());}
 if(k%8==6){input.push_back(0x40010);input.push_back(rnd());}
 if(k%5)input.push_back((rnd()&0xffffffcu)|1);
 }else if(input.back()%4==1)input.back()=(rnd()&0xffffffcu)|1;
 unsigned cnt=0,p=0;reference(cnt,p);
 for(unsigned m=0;m<2;m++){calls=0;bool hit=(m?SpanPush:CachedPush)(0x84080000,input.size()*4);
 if(hit){admitted[m]++;if(cnt!=1||calls!=1||p!=primitive||wanted!=emitted)abort();}else if(calls)abort();}
 }
 printf("50000 packets, verified admitted cache=%u span=%u\n",admitted[0],admitted[1]);}
