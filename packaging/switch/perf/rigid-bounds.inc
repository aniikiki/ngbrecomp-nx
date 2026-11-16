/* Diagnostic only. Rigid XYZ fixed-function triangles use the uploaded WVP
 * directly. Include every position in the bound stream span, even vertices
 * outside the index list. Do not classify unsupported formats or bad data. */
static unsigned RigidBoundsPrediction(const gpu::Assembled& a, const float *m)
{
    if (!(a.regs & 1) || a.topology != gpu::Topology::Triangles || a.pretransformed) return 0;
    const auto& e=a.elements[0];
    if ((e.format!=6 && e.format!=2) || e.buffer>=a.buffer_count) return 0;
    const auto& b=a.buffers[e.buffer];
    if(!b.src || b.stride<12 || e.offset+12u>b.stride || e.offset+12u>b.bytes) return 0;
    unsigned n=1+(b.bytes-e.offset-12)/b.stride;
    if (!n || n>65536) return 0;
    double lo[3]={1e12,1e12,1e12},hi[3]={-1e12,-1e12,-1e12};
    for(unsigned i=0;i<n;i++){
        float xyz[3];std::memcpy(xyz,b.src+size_t(i)*b.stride+e.offset,12);
        for(unsigned j=0;j<3;j++){
            if(!(std::abs(xyz[j])<1e10f))return 0;
            lo[j]=std::min(lo[j],double(xyz[j]));hi[j]=std::max(hi[j],double(xyz[j]));
        }
    }
    for(unsigned i=0;i<16;i++)if(!(std::abs(m[i])<1e10f))return 0;
    for(unsigned axis=0;axis<2;axis++)for(int sign:{-1,1}){
        double top=double(m[15])+sign*double(m[axis*4+3]);
        double magnitude=std::abs(double(m[15]))+std::abs(double(m[axis*4+3]));
        for(unsigned j=0;j<3;j++){
            double w=m[12+j],v=m[axis*4+j],c=w+sign*v;
            top+=c*(c>0?hi[j]:lo[j]);
            magnitude+=(std::abs(w)+std::abs(v))*std::max(std::abs(hi[j]),std::abs(lo[j]));
        }
        // Bound single-precision multiply/add and remain outside by a margin.
        if(top < -(1e-5*magnitude+1e-4))return 2;
    }
    // Vulkan's standard homogeneous near and far planes: z>=0, w-z>=0.
    // Report separately until matched to the original draw's GPU statistics.
    for (unsigned plane=0; plane<2; ++plane) {
        double top=0, magnitude=0;
        for(unsigned j=0;j<4;j++){
            double z=m[8+j],w=plane?m[12+j]:0;
            double coef=plane?w-z:z;
            top+=coef*(j==3?1:(coef>0?hi[j]:lo[j]));
            magnitude+=(std::abs(w)+std::abs(z))*(j==3?1:std::max(std::abs(hi[j]),std::abs(lo[j])));
        }
        if(top < -(1e-5*magnitude+1e-4))return 3+plane;
    }
    return 1;
}
