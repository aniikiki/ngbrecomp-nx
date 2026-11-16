// Offline feasibility: can a cached world-space center plus one inflated
// sphere reject a whole candidate before constructing the guest matrices?
// Report disagreements against both the original ordered arithmetic and
// observed return. No guest state is ever changed in this tool.
#include <cstdio>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>
#include <algorithm>
struct Row {uint32_t h[6];float actor[16],pos[3],bone[16],ball[4],box[7];uint32_t result;};
static_assert(sizeof(Row)==53*4);
int main(int argc,char**argv){
 if(argc!=3)return 1;FILE*f=fopen(argv[1],"rb"),*x=fopen(argv[2],"rb");if(!f||!x)return 2;
 auto u32=[&](unsigned off){uint32_t n=0;fseek(x,off,SEEK_SET);if(fread(&n,4,1,x)!=1)std::abort();return n;};
 unsigned base=u32(0x104),n=u32(0x11c),tab=u32(0x120)-base;float pad=NAN;
 for(unsigned i=0;i<n;i++){unsigned a=tab+i*56,va=u32(a+4),bytes=u32(a+16),raw=u32(a+12);
  if(0x4149c4u-va<bytes){unsigned b=u32(raw+0x4149c4-va);memcpy(&pad,&b,4);}}
 if(!std::isfinite(pad))return 3;
 // One enclosure per descriptor, rebuilt only when actor, bone, translation or
 // local bounds bytes change. Radius varies with each query, so store the
 // radius coefficient separately from the unexpanded world half-extents.
 struct Cache {uint32_t key[3];unsigned char bytes[168];double center[3],span[3],slope[3];int set;};
 Cache bank[16][4]{};unsigned builds=0,hits=0;Row r;unsigned total=0,reject=0,orig=0,false_rej=0,false_hit=0,ill=0;
 while(fread(&r,sizeof r,1,f)==1){
  total++;float m[4][4];memcpy(r.actor+12,r.pos,12);r.actor[15]=1;
  for(int i=0;i<4;i++)for(int j=0;j<4;j++)m[i][j]=((r.bone[4*i]*r.actor[j]+r.bone[4*i+1]*r.actor[j+4])+r.bone[4*i+2]*r.actor[j+8])+r.bone[4*i+3]*r.actor[j+12];
  float rad=r.ball[3]+pad;bool original=false;
  for(int i=0;i<3;i++){float inv=(-m[3][0]*m[i][0]+ -m[3][1]*m[i][1])+ -m[3][2]*m[i][2];
   float center=((r.ball[0]*m[i][0]+inv)+r.ball[1]*m[i][1])+r.ball[2]*m[i][2];
   float delta=r.box[i]-center;
   original|=(r.box[4+i]+delta)+rad<0 || delta-rad>0;}
  orig+=original;
  // Invert the 3x3 world->local projection explicitly. Rig scaling and shear
  // are allowed. Infinity norm yields a conservative cube enclosing the
  // padded box. Large magnitude/poor conditioning fall back to original.
  double a[3][3],v[3],dist[3];double mx=0;
  for(int i=0;i<3;i++)for(int j=0;j<3;j++){a[i][j]=m[i][j];mx=std::max(mx,std::abs(a[i][j]));}
  double det=a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])-a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])+a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]);
  if(std::abs(det)<.001 || !(mx<32) || !std::isfinite(rad) || rad<0){ill++;continue;}
  bool ok=false;
  uint32_t key[]={r.h[1],r.h[2],r.h[4]};unsigned char bytes[168];
  memcpy(bytes,r.actor,64);memcpy(bytes+64,r.pos,12);memcpy(bytes+76,r.bone,64);memcpy(bytes+140,r.box,28);
  auto& bucket=bank[((key[2]>>5)^(key[1]>>6)^(key[0]>>10))&15];
  unsigned idx=0;while(idx<4 && bucket[idx].set && memcmp(key,bucket[idx].key,sizeof key))++idx;
  idx=std::min(3u,idx);
  Cache chosen=bucket[idx];while(idx){bucket[idx]=bucket[idx-1];--idx;}bucket[0]=chosen;
  auto &item=bucket[0];
  if(!item.set || memcmp(key,item.key,sizeof key) || memcmp(bytes,item.bytes,sizeof bytes)){
   ++builds;item.set=1;memcpy(item.key,key,sizeof key);memcpy(item.bytes,bytes,sizeof bytes);
   for(int i=0;i<3;i++){v[i]=r.box[i]+r.box[4+i]*.5;dist[i]=r.box[4+i]*.5;}
   for(int i=0;i<3;i++){
    double mid=m[3][i],bound=0,slope=0;
    for(int j=0;j<3;j++){
     double c=(a[(j+1)%3][(i+1)%3]*a[(j+2)%3][(i+2)%3]-a[(j+1)%3][(i+2)%3]*a[(j+2)%3][(i+1)%3])/det;
     mid+=c*v[j];bound+=std::abs(c)*dist[j];slope+=std::abs(c);}
    item.center[i]=mid;item.span[i]=bound;item.slope[i]=slope;
   }
  }else hits++;
  for(unsigned i=0;i<3;i++)ok|=std::abs(r.ball[i]-item.center[i])>item.span[i]+item.slope[i]*rad+.02;
  if(ok){reject++;false_rej+=!original;false_hit+=r.result!=0;}
 }
 printf("samples=%u original_plane_rejects=%u cached_world_AABB_rejects=%u contradict_planes=%u contradict_return=%u fallback=%u pad=%f\n",total,orig,reject,false_rej,false_hit,ill,pad);
 printf("stable descriptor cache hits=%u builds=%u\n",hits,builds);
 return ferror(f)||false_rej||false_hit;
}
