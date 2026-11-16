// Run: c++ -std=c++20 -O2 -Isrc/d3d packaging/switch/perf/verify-rigid-clip.cpp -o /tmp/ngb-verify-clip
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
#include <random>
#include <vector>
#include "gpu/vertex.h"
#include "vk/rigid_clip.h"

using V = std::array<double,4>;
using P = std::array<float,3>;
using Triangle = std::array<P,3>;
using M = std::array<float,16>;

// Independent reference: actually clip this triangle in homogeneous space,
// retaining edges that cross a side even when no original vertex lies inside.
static bool reaches_frustum(const Triangle& tri, const M& m) {
    std::vector<V> polygon;
    for (auto& p : tri) {
        V v{};
        for (unsigned r=0;r<4;++r)
            v[r]=double(p[0])*m[4*r]+double(p[1])*m[4*r+1]+double(p[2])*m[4*r+2]+m[4*r+3];
        polygon.push_back(v);
    }
    for (unsigned k=0;k<4 && !polygon.empty();++k) {
        auto distance=[&](const V& v){return v[3]+(k%2?-v[k/2]:v[k/2]);};
        std::vector<V> inside;
        auto a=polygon.back(); double da=distance(a);
        for (auto b : polygon) {
            double db=distance(b);
            if ((da<0)!=(db<0)) {
                V h{};double t=da/(da-db);
                for (unsigned j=0;j<4;++j)h[j]=a[j]+t*(b[j]-a[j]);
                inside.push_back(h);
            }
            if(db>=0)inside.push_back(b);
            a=b;da=db;
        }
        polygon.swap(inside);
    }
    return !polygon.empty();
}
int main() {
    Triangle tri={{{2,0,0},{2,1,0},{3,-1,0}}};
    M m={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    gpu::Assembled a;
    a.regs=1;a.buffer_count=1;a.elements[0]={6,0,0};
    a.buffers[0]={reinterpret_cast<const uint8_t*>(tri.data()),sizeof(tri),sizeof(P)};
    auto reject=[&]{return OutsideRigidClip(a,m.data());};
    assert(reject());
    tri[0][0]=1;assert(!reject());                   // touches boundary
    tri[0][0]=std::nextafter(1.f,2.f);assert(!reject());
    tri[0][0]=std::numeric_limits<float>::quiet_NaN();assert(!reject());
    tri={{{-3,-2,0},{3,-2,0},{0,3,0}}};assert(!reject() && reaches_frustum(tri,m));
    std::mt19937 rng(66853);
    std::uniform_real_distribution<float> val(-4,4);
    unsigned outside=0,visible=0;
    for(unsigned i=0;i<100000;i++){
        float scale=std::ldexp(1.f,int(rng()%45)-22);
        for(auto& row:tri)for(auto& x:row)x=val(rng);
        for(auto& x:m)x=val(rng)*scale;
        bool cut=reject(),vis=reaches_frustum(tri,m);
        assert(!(cut && vis));
        outside+=cut;visible+=vis;
    }
    assert(outside>1000 && visible>1000);
    std::printf("100000 independent homogeneous triangle clips: %u predicted outside, %u visible, no false rejects\n",outside,visible);
}
