// Real Vulkan feedback: four aliased headers must all read the picture before
// this draw, and the next draw must take a new picture after a clear.
static void NativeEffectContract() {
    auto require = [](bool okay, unsigned detail) {
        if (!okay) ngb_stop("native effect contract failed", detail);
    };
    uint32_t scratch = NativePool(4096);
    uint32_t surface = NativeCreateSurface(8, 4, 0x12);
    gpu::State s = g_state;
    s.rt = SurfaceOf(surface); s.zs = {};
    s.viewport = {0, 0, 8, 4, 0, 1}; s.scissor_count = 0;
    s.vs.reset(); s.ps.reset(); s.vs_handle = 0x144;
    s.rs[gpu::kRsLighting] = s.rs[gpu::kRsCullMode] = s.rs[gpu::kRsZEnable] = 0;
    s.rs[gpu::kRsStencilEnable] = s.rs[gpu::kRsFogEnable] = s.rs[gpu::kRsVertexBlend] = 0;
    s.simple[gpu::kMBlendEnable >> 2] = s.simple[gpu::kMAlphaTestEnable >> 2] = 0;
    s.simple[gpu::kMColorWriteEnable >> 2] = 0x01010101;
    s.palettes.fill(0);
    for (unsigned i = 0; i < 4; ++i) {
        uint32_t alias = scratch + i * 32;
        std::memcpy(HostPtr(alias, 20), HostPtr(surface, 20), 20);
        s.textures[i] = alias;
        auto& t = s.tss[i]; t.fill(0);
        t[gpu::kTssColorOp] = i ? 7 : 2; // add the same texture four times
        t[gpu::kTssColorArg1] = 2; t[gpu::kTssColorArg2] = 1;
        t[gpu::kTssAlphaOp] = 2; t[gpu::kTssAlphaArg1] = 2;
        t[gpu::kTssResultArg] = 1;
        t[gpu::kTssAddressU] = t[gpu::kTssAddressV] = t[gpu::kTssAddressW] = 3;
        t[gpu::kTssMinFilter] = t[gpu::kTssMagFilter] = 1;
    }
    struct Vertex { float x, y, z, w; uint32_t colour; float u, v; };
    Vertex quad[] = {{0,0,.5f,1,~0u,0,0}, {8,0,.5f,1,~0u,8,0},
                     {8,4,.5f,1,~0u,8,4}, {0,4,.5f,1,~0u,0,4}};
    std::memcpy(HostPtr(scratch + 256, sizeof quad), quad, sizeof quad);
    W32(scratch + 128, 0x80000001); W32(scratch + 132, scratch + 256);
    s.streams[0] = {scratch + 128, sizeof(Vertex)};
    gpu::TextureDesc d; require(gpu::Describe(surface, d), 1);
    for (auto colours : {std::pair{0xff404040u, 0xffffffffu}, std::pair{0xff004000u, 0xff00ff00u}}) {
        g_backend->Clear(s, 0, nullptr, gpu::kClearTarget, colours.first, 1, 0);
        g_backend->Draw(s, 8, 0, 4, nullptr); // QUADLIST
        g_backend->Copy(s.rt, s.rt, 0, nullptr, nullptr);
        g_backend->Sync(d.data, gpu::TotalSize(d));
        for (unsigned y = 0; y < 4; ++y) for (unsigned x = 0; x < 8; ++x)
            require(R32(d.data + y * d.pitch + x * 4) == colours.second, 0x100 + y * 8 + x);
    }

    // The same blended material alternates between the pass-through shader
    // and a real alpha compare. Its independent texture kill must still work.
    uint32_t output = NativeCreateSurface(8, 4, 0x12);
    constexpr uint32_t transparent = 0x00336699, background = 0xff123456;
    g_backend->Clear(s, 0, nullptr, gpu::kClearTarget, transparent, 1, 0);
    s.rt = SurfaceOf(output);
    s.textures.fill(0); s.textures[0] = surface;
    s.tss[1][gpu::kTssColorOp] = 1;
    s.simple[gpu::kMBlendEnable >> 2] = 1;
    s.simple[gpu::kMSrcBlend >> 2] = 1;
    s.simple[gpu::kMDestBlend >> 2] = 0;
    s.simple[gpu::kMBlendOp >> 2] = 0x8006;
    s.simple[gpu::kMAlphaRef >> 2] = 0;
    require(gpu::Describe(output, d), 3);
    struct AlphaCase { unsigned enabled, function, kill; uint32_t expected; };
    const AlphaCase cases[] = {{0, 0x204, 0, transparent}, {1, 0x204, 0, background},
                               {1, 0x207, 0, transparent}, {0, 0x207, 4, background},
                               {0, 0x204, 0, transparent}};
    for (const auto& test : cases) {
        s.simple[gpu::kMAlphaTestEnable >> 2] = test.enabled;
        s.simple[gpu::kMAlphaFunc >> 2] = test.function;
        s.tss[0][gpu::kTssAlphaKill] = test.kill;
        g_backend->Clear(s, 0, nullptr, gpu::kClearTarget, background, 1, 0);
        g_backend->Draw(s, 8, 0, 4, nullptr);
        g_backend->Sync(d.data, gpu::TotalSize(d));
        for (unsigned y = 0; y < 4; ++y) for (unsigned x = 0; x < 8; ++x)
            require(R32(d.data + y * d.pitch + x * 4) == test.expected, 0x300 + y * 8 + x);
    }
    std::fprintf(stderr, "[ALPHA-CONTRACT-PASS] blend alpha state switches and texture-stage kill\n");

    // Reuse one target address at different sizes while older frames still
    // own its images. The latest colour survives; validation checks retirement.
    uint32_t changing = NativeHeader(20), data = NativeData(4096);
    W32(changing, 0x01040001); W32(changing + 4, data);
    s.textures.fill(0);
    for (unsigned i = 0; i < 8; ++i) {
        unsigned w = (i & 1) ? 16 : 8, h = (i & 1) ? 8 : 4;
        NativeTextureHeader(w, h, 1, 1, 0x12, 0, false, false, changing + 12, changing + 16);
        s.rt = SurfaceOf(changing); s.viewport = {0, 0, w, h, 0, 1};
        g_backend->Clear(s, 0, nullptr, gpu::kClearTarget, 0xff123400u + i, 1, 0);
        g_backend->Present(s.rt); g_backend->FrameWait();
    }
    require(gpu::Describe(changing, d), 2);
    g_backend->Sync(d.data, gpu::TotalSize(d));
    for (unsigned y = 0; y < d.height; ++y) for (unsigned x = 0; x < d.width; ++x)
        require(R32(d.data + y * d.pitch + x * 4) == 0xff123407u, 0x200 + y * 16 + x);
    std::fprintf(stderr, "[EFFECT-CONTRACT-PASS] feedback aliases, fresh contents, in-flight resize\n");
}

// A depth/stencil image must remain a usable shadow map after rendering and
// on the next frame. Check the sampled result, not only the depth readback.
static void NativeShadowContract() {
    auto require = [](bool okay, unsigned detail) {
        if (!okay) ngb_stop("native shadow contract failed", detail);
    };
    uint32_t scratch = NativePool(4096);
    uint32_t colour = NativeCreateSurface(16, 8, 0x12);
    uint32_t depth = NativeCreateSurface(16, 8, 0x2e);
    gpu::State s = g_state;
    s.rt = {}; s.zs = SurfaceOf(depth); s.viewport = {0,0,16,8,0,1}; s.scissor_count = 0;
    s.vs.reset(); s.ps.reset(); s.vs_handle = 0x20104; // XYZRHW and four texture coordinates
    s.textures.fill(0); s.palettes.fill(0);
    s.rs[gpu::kRsLighting] = s.rs[gpu::kRsCullMode] = s.rs[gpu::kRsZEnable] = 0;
    s.rs[gpu::kRsStencilEnable] = s.rs[gpu::kRsFogEnable] = s.rs[gpu::kRsVertexBlend] = 0;
    s.rs[gpu::kRsShadowFunc] = 0x206; // texel depth >= projected receiver depth
    s.simple[gpu::kMBlendEnable >> 2] = s.simple[gpu::kMAlphaTestEnable >> 2] = 0;
    s.simple[gpu::kMColorWriteEnable >> 2] = 0x01010101;
    for (auto& t : s.tss) t.fill(0);
    auto& t = s.tss[0];
    t[gpu::kTssColorOp] = t[gpu::kTssAlphaOp] = 2;
    t[gpu::kTssColorArg1] = t[gpu::kTssAlphaArg1] = 2;
    t[gpu::kTssResultArg] = 1;
    t[gpu::kTssAddressU] = t[gpu::kTssAddressV] = t[gpu::kTssAddressW] = 3;
    t[gpu::kTssMinFilter] = t[gpu::kTssMagFilter] = 1;
    struct Vertex { float x,y,z,w,u,v,r,q; };
    const float reference = 16777215.f * .5f;
    const Vertex quad[] = {{0,0,.5f,1,0,0,reference,1}, {16,0,.5f,1,16,0,reference,1},
                           {16,8,.5f,1,16,8,reference,1}, {0,8,.5f,1,0,8,reference,1}};
    std::memcpy(HostPtr(scratch + 256, sizeof quad), quad, sizeof quad);
    W32(scratch,0x80000001); W32(scratch + 4,scratch + 256);
    s.streams[0] = {scratch,sizeof(Vertex)};
    gpu::TextureDesc d; require(gpu::Describe(colour,d),1);
    for (unsigned frame = 0; frame < 3; ++frame) {
        s.rt = {}; s.zs = SurfaceOf(depth); s.textures[0] = 0;
        g_backend->Clear(s,0,nullptr,gpu::kClearZ | gpu::kClearStencil,0,1,0x53);
        uint32_t rect[] = {0,0,8,8};
        g_backend->Clear(s,1,reinterpret_cast<const uint8_t*>(rect),gpu::kClearZ,0,frame == 1 ? .75f : .25f,0);
        s.rt = SurfaceOf(colour); s.zs = {}; s.textures[0] = depth;
        g_backend->Draw(s,8,0,4,nullptr);
        g_backend->Present(s.rt); g_backend->FrameWait();
        g_backend->Sync(d.data,gpu::TotalSize(d));
        for (unsigned y = 2; y < 6; ++y) for (unsigned x : {2u,13u}) {
            uint32_t expected = x < 8 && frame != 1 ? 0 : 0xffffff;
            require((R32(d.data + y*d.pitch + x*4) & 0xffffff) == expected,0x100 + frame*128 + y*16 + x);
        }
    }
    std::fprintf(stderr,"[SHADOW-CONTRACT-PASS] depth/stencil map sampled correctly across three frames\n");
}

// The same additive quad is drawn twice against a split-depth background.
// BC3 alpha includes soft values and a repeat seam. Both paths must agree
// in every channel, including the pixels on the occluded side of the blade.
static void NativeCombatContract() {
    using namespace gpu;
    constexpr uint32_t width = 96, height = 64, background = 0x54231c17;
    const uint32_t colour = NativeCreateSurface(width,height,0x12);
    const uint32_t depth = NativeCreateSurface(width,height,0x2e);
    const uint32_t texture = NativeHeader(20);
    const uint32_t bytes = NativeTextureHeader(64,64,1,1,0x0f,0,false,false,texture+12,texture+16);
    W32(texture,0x01040001); W32(texture+4,NativeData(bytes));
    TextureDesc tex, target;
    if (!Describe(texture,tex) || !Describe(colour,target)) ngb_stop("UT fixture surface",0);
    auto* blocks = static_cast<uint8_t*>(HostPtr(tex.data,bytes));
    // One slanted stripe, feathered at both edges.
    for (unsigned by=0;by<16;++by) for (unsigned bx=0;bx<16;++bx) {
        uint8_t* b = blocks + (by*16+bx)*16;
        std::memset(b,0,16); b[0]=255; b[8]=0xff; b[9]=0xff;
        uint64_t codes=0;
        for (int y=0;y<4;++y) for(int x=0;x<4;++x) {
            int u=int(bx*4)+x, v=int(by*4)+y, d=std::abs(u-v);
            unsigned code=(u<5 || u>58 || v<5 || v>58 || d>5) ? 1 : d>=3 ? 5 : 0;
            codes |= uint64_t(code) << (3*(y*4+x));
        }
        std::memcpy(b+2,&codes,6);
    }
    State s=g_state;
    s.rt=SurfaceOf(colour); s.zs=SurfaceOf(depth); s.viewport={0,0,width,height,0,1};
    s.scissor_count=0; s.vs.reset(); s.ps.reset(); s.vs_handle=0x142;
    for (unsigned matrix : {2u,3u,256u}) {
        s.transforms[matrix].fill(0);
        for(unsigned i=0;i<4;++i) s.transforms[matrix][5*i]=1;
    }
    s.rs[kRsLighting]=s.rs[kRsCullMode]=s.rs[kRsFogEnable]=s.rs[kRsVertexBlend]=0;
    s.rs[kRsStencilEnable]=s.rs[kRsSpecularEnable]=0;
    s.rs[kRsZEnable]=1; s.rs[kRsTextureFactor]=0xb5ffffff;
    s.simple[kMZFunc/4]=0x203; s.simple[kMZWriteEnable/4]=0;
    s.simple[kMColorWriteEnable/4]=0x01010101;
    s.simple[kMBlendEnable/4]=1; s.simple[kMSrcBlend/4]=0x302;
    s.simple[kMDestBlend/4]=1; s.simple[kMBlendOp/4]=0x8006; s.simple[kMAlphaTestEnable/4]=0;
    s.palettes.fill(0); s.textures.fill(0); s.textures[0]=texture;
    for(auto& t:s.tss) {t.fill(0); t[kTssColorOp]=1;}
    auto& t=s.tss[0];
    t[kTssColorOp]=t[kTssAlphaOp]=4;
    t[kTssColorArg1]=t[kTssAlphaArg1]=2; t[kTssColorArg2]=t[kTssAlphaArg2]=t[kTssResultArg]=1;
    t[kTssAddressU]=t[kTssAddressV]=t[kTssAddressW]=1; t[kTssMinFilter]=t[kTssMagFilter]=2;
    auto& second=s.tss[1]; second[kTssColorOp]=3; second[kTssColorArg2]=1;
    second[kTssAlphaOp]=4; second[kTssAlphaArg1]=3; second[kTssAlphaArg2]=second[kTssResultArg]=1;
    struct V {float x,y,z; uint32_t colour; float u,v;};
    const V vertices[]={{-1,-1,.5f,0xb0c08070,0,-1},{1,-1,.5f,0xb0c08070,1,-1},
                        {-1,1,.5f,0xb0c08070,0,0},{1,1,.5f,0xb0c08070,1,0}};
    uint32_t vb=NativePool(256);
    W32(vb,0x80000001); W32(vb+4,vb+32);
    std::memcpy(HostPtr(vb+32,sizeof vertices),vertices,sizeof vertices);
    s.streams[0]={vb,sizeof(V)};
    std::vector<uint32_t> expected(width*height);
    unsigned visible=0;
    for (auto role : {CombatEffect::None,CombatEffect::Transparent}) {
        g_backend->Clear(s,0,nullptr,kClearTarget|kClearZ|kClearStencil,background,1,0);
        const uint32_t rect[]={0,0,width/2,height};
        g_backend->Clear(s,1,reinterpret_cast<const uint8_t*>(rect),kClearZ,0,0.25f,0);
        g_backend->Draw(s,6,0,4,nullptr,nullptr,role);
        g_backend->Flush(); g_backend->Sync(target.data,TotalSize(target));
        for (unsigned y=0;y<height;++y) for(unsigned x=0;x<width;++x) {
            uint32_t p=R32(target.data+y*target.pitch+x*4);
            auto& ref=expected[y*width+x];
            if (role==CombatEffect::None) {
                ref=p; visible+=p!=background;
                if (x<width/2 && p!=background) ngb_stop("UT depth mask",y*width+x);
            } else if (p!=ref) ngb_stop("UT additive colour/alpha mismatch",y*width+x);
        }
    }
    if (visible<20 || visible>width*height/3) ngb_stop("UT visible stripe",visible);
    std::fprintf(stderr,"[UT-CONTRACT-PASS] %u RGBA pixels, %u visible, split depth\n",width*height,visible);
}

struct NativePresentProbe {
    std::mutex mutex;
    std::condition_variable changed;
    bool consumed = false, allow = false, returned = false, rescued = false;
};
class NativePresentBackend final : public gpu::Backend {
    NativePresentProbe& probe;
public:
    explicit NativePresentBackend(NativePresentProbe& p): probe(p) {}
    bool Init(uint32_t, uint32_t) override { return true; }
    void Clear(const gpu::State&,uint32_t,const uint8_t*,uint32_t,uint32_t,float,uint32_t) override {}
    void Draw(const gpu::State&,uint32_t,uint32_t,uint32_t,const uint8_t*,const gpu::IndexBounds*,gpu::CombatEffect) override {}
    void Copy(const gpu::Surface&,const gpu::Surface&,uint32_t,const uint8_t*,const uint8_t*) override {}
    void Sync(uint32_t,uint32_t) override {}
    void SyncLate(uint32_t) override {}
    void Flush() override {}
    void SetGamma(const uint8_t*) override {}
    void Present(const gpu::Surface& s) override { Present(s, nullptr, nullptr); }
    void Present(const gpu::Surface&, void (*consumed)(void*), void* context) override {
        if (consumed) consumed(context);
        std::unique_lock lock(probe.mutex);
        probe.consumed = true; probe.changed.notify_all();
        probe.changed.wait(lock, [&] { return probe.allow; });
    }
};

static void NativePresentContract() {
    auto require = [](bool okay, unsigned detail) {
        if (!okay) ngb_stop("native present contract failed", detail);
    };
    NativePresentProbe p;
    g_backend = gpu::CreateThreadedBackend(std::make_unique<NativePresentBackend>(p));
    require(g_backend->Init(8, 4), 1);
    g_backend->Present({});
    {
        std::unique_lock lock(p.mutex);
        require(p.changed.wait_for(lock, std::chrono::seconds(2), [&] { return p.consumed; }), 2);
    }
    g_backend->Present({}); // FrameWait now names the first, deliberately stalled present.
    uint32_t fence = g_backend->Fence();
    std::thread rescue([&] {
        std::unique_lock lock(p.mutex);
        if (!p.changed.wait_for(lock, std::chrono::seconds(2), [&] { return p.returned; })) p.rescued = true;
        p.allow = true; p.changed.notify_all();
    });
    g_backend->FrameWait();
    bool fence_pending = g_backend->FencePending(fence);
    {
        std::lock_guard lock(p.mutex);
        p.returned = true; p.changed.notify_all();
    }
    rescue.join();
    g_backend->WaitFence(fence);
    require(!p.rescued && fence_pending && !g_backend->FencePending(fence), 3);
    g_backend.reset();
    std::fprintf(stderr, "[PRESENT-CONTRACT-PASS] frame input consumed before presentation; fences still wait\n");
}
