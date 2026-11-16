// A common side plane must exclude EVERY vertex. Stop as soon as two vertices
// disagree on all possible separating planes. No persistent buffer identity.
static bool OutsideRigidClip(const gpu::Assembled& a, const float* m) {
    if (!(a.regs & 1) || a.topology != gpu::Topology::Triangles || a.pretransformed) return false;
    const auto& e=a.elements[0];
    if ((e.format!=6 && e.format!=2) || e.buffer>=a.buffer_count) return false;
    const auto& b=a.buffers[e.buffer];
    if(!b.src || b.stride<12 || e.offset+12u>b.stride || e.offset+12u>b.bytes) return false;
    const unsigned n=1+(b.bytes-e.offset-12)/b.stride;
    if (!n || n>65536) return false;
    float largest=0;
    for(unsigned i=0;i<16;i++){
        float v=std::abs(m[i]); if(!(v<1e10f))return false;
        largest=std::max(largest,v);
    }
    const float fudge=largest*2e-5f; // bounds both four-term dots + plane addition in float
    unsigned mask=15;
    for(unsigned i=0;i<n;i++){
        float p[3];std::memcpy(p,b.src+size_t(i)*b.stride+e.offset,12);
        float sum=std::abs(p[0])+std::abs(p[1])+std::abs(p[2])+1;
        if(!(sum<1e10f))return false;
        auto dot=[&](unsigned o){return p[0]*m[o]+p[1]*m[o+1]+p[2]*m[o+2]+m[o+3];};
        float x=dot(0),y=dot(4),w=dot(12),tol=-(sum*fudge+1e-4f);
        unsigned sides=unsigned(w+x<tol)|(unsigned(w-x<tol)<<1)|(unsigned(w+y<tol)<<2)|(unsigned(w-y<tol)<<3);
        mask &= sides;
        if(!mask)return false;
    }
    return true;
}
