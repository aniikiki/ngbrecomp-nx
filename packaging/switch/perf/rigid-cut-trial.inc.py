# Executed by visibility-work.py: private replay only. Never uses occlusion
# feedback or changes commands that contribute to an Xbox visibility report.
tag = 'void VulkanBackend::CapturePeek('
helper = Path(__file__).with_name(helper_name).read_text()
matrix="    float vpm[16];RigidViewport(s,gw,gh,vpm);RigidMatrices(s,vpm,wv,m);"
replace(tag, helper + '''
static uint64_t rigid_ns() {
    timespec t; clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
    return uint64_t(t.tv_sec)*1000000000+t.tv_nsec;
}
static bool rigid_cut(const State& s,const Assembled& a,const Surface& surface) {
    if(a.pretransformed || a.topology!=Topology::Triangles || s.rs[kRsVertexBlend] ||
       (s.vs_handle!=0x142 && s.vs_handle!=0x152 && s.vs_handle!=0x112))return false;
    uint32_t gw,gh;SurfaceSize(surface,gw,gh);
    if (!gw || !gh) return false;
    float wv[16],wvp[16],full[16],m[16];
''' + matrix + '''
    
    return RigidBoundsPrediction(a,m)==2;
}
''' + tag)
tag='    bool vis_on_ = false;'
replace(tag,tag+'''
    unsigned rigid_frame_=0,rigid_off_=0; uint64_t rigid_start_=0;
    bool rigid_alternate() const {return ((rigid_frame_ ^ (rigid_frame_>>1))&1)!=0;}
''')
tag='    st_.draws++;'
replace(tag,tag+' if(!rigid_start_)rigid_start_=rigid_ns();')
tag='    rt_draws_[s.rt.data]++;'
replace(tag,tag+'''
    if (rigid_alternate() && !vis_on_ && !ContinuousGlowEnabled() &&
        rigid_cut(s,a,rt?s.rt:s.zs)) {++rigid_off_;return;}
''')
tag='void VulkanBackend::Present(const Surface& front) {'
replace(tag,tag+'''
    unsigned phase=__atomic_load_n(&ngb_coverage_frame,__ATOMIC_RELAXED);
    if(phase>=1650 && rigid_start_)std::fprintf(stderr,"[CUT] %u %u %u %llu %u %u %u\\n",
       phase,rigid_frame_,unsigned(rigid_alternate()),(unsigned long long)(rigid_ns()-rigid_start_),
       st_.draws,st_.drawn,rigid_off_);
    ++rigid_frame_;rigid_off_=0;rigid_start_=0;
''')
