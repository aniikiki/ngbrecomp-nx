extern "C" void ngb_test_submission_counts(uint64_t*);
extern "C" uint64_t ngb_test_unindexed_draws();

static std::array<uint32_t,3> NativeSubmissionContract() {
    auto require = [](bool okay, unsigned detail) {
        if (!okay) ngb_stop("native submission contract failed", detail);
    };
    const char* samples = std::getenv("NGB_REPLAY_MSAA");
    bool multisampled = samples && std::atoi(samples) > 1;
    const char* scale = std::getenv("NGB_D3D_SCALE");
    bool scaled_resolve = multisampled && scale && std::strcmp(scale, "1") != 0;
    uint32_t width = multisampled ? 640 : 16, height = multisampled ? 480 : 8;
    uint32_t scratch = NativePool(4096), surface = NativeCreateSurface(width, height, 0x12);
    uint32_t copy = NativeCreateSurface(width, height, 0x12), vertex = scratch + 64, report = scratch + 128;
    struct Vertex { float x, y, z, w; uint32_t colour; };
    Vertex vertices[16]; // large enough to exercise the cached geometry allocation
    W32(vertex, 0x80000001); W32(vertex + 4, scratch + 512);
    gpu::State s = g_state;
    s.rt = SurfaceOf(surface); s.zs = {}; s.viewport = {0,0,16,8,0,1}; s.scissor_count = 0;
    s.vs.reset(); s.ps.reset(); s.vs_handle = 0x44;
    s.textures.fill(0); s.palettes.fill(0); s.streams[0] = {vertex, sizeof(Vertex)};
    s.rs[gpu::kRsLighting] = s.rs[gpu::kRsCullMode] = s.rs[gpu::kRsZEnable] = 0;
    s.rs[gpu::kRsStencilEnable] = s.rs[gpu::kRsFogEnable] = s.rs[gpu::kRsVertexBlend] = 0;
    s.simple[gpu::kMBlendEnable >> 2] = s.simple[gpu::kMAlphaTestEnable >> 2] = 0;
    s.simple[gpu::kMColorWriteEnable >> 2] = 0x01010101;
    const uint32_t colours[] = {0xffff0000,0xff00ff00,0xff0000ff,0xffffff00};
    const char* option = std::getenv("NGB_D3D_ASYNC_SUBMIT");
    bool enabled = !option || std::strcmp(option,"0") != 0;
    for (unsigned frame = 0; frame < 3; ++frame) {
        g_backend->Flush(); g_backend->WaitFence(g_backend->Fence());
        uint64_t before[4], after[4]; ngb_test_submission_counts(before);
        g_backend->Clear(s,0,nullptr,gpu::kClearTarget,0xff000000,1,0);
        W32(report + 12,~0u); g_backend->VisibilityBegin();
        for (unsigned block = 0; block < 4; ++block) {
            // The recorder fence protects the guest bytes, but never waits for
            // Vulkan here. Already uploaded geometry must survive these writes.
            g_backend->WaitFence(g_backend->Fence());
            float x = (block & 1) ? 4 : 0, y = (block & 2) ? 2 : 0;
            uint32_t colour = colours[(block + frame) % 4];
            for (unsigned q = 0; q < 4; ++q) {
                vertices[q*4] = {x,y,.5f,1,colour}; vertices[q*4+1] = {x+4,y,.5f,1,colour};
                vertices[q*4+2] = {x+4,y+2,.5f,1,colour}; vertices[q*4+3] = {x,y+2,.5f,1,colour};
            }
            std::memcpy(HostPtr(scratch+512,sizeof vertices),vertices,sizeof vertices);
            for (unsigned i = 0; i < 160; ++i) g_backend->Draw(s,8,0,16,nullptr);
            if (block == 1) g_backend->VisibilityEnd(report); // spans the first asynchronous submit
        }
        g_backend->WaitFence(g_backend->Fence()); ngb_test_submission_counts(after);
        require(after[0]-before[0] == (enabled ? 3u : 0u),1);
        require(after[1]==before[1] && after[2]==before[2] && after[3]==before[3],2);
        g_backend->Copy(s.rt,SurfaceOf(copy),0,nullptr,nullptr);
        for (uint32_t target : {surface,copy}) {
            gpu::TextureDesc d; require(gpu::Describe(target,d),3);
            g_backend->Sync(d.data,gpu::TotalSize(d));
            for (unsigned y=0;y<8;++y) for (unsigned x=0;x<16;++x) {
                // At scaled MSAA the guest readback samples the resolved image.
                // Test inside each colour block, away from its coverage edges.
                if (scaled_resolve && (!(y & 1) || (x & 3) == 0 || (x & 3) == 3)) continue;
                unsigned block=(x>=4 ? 1 : 0)+(y>=2 ? 2 : 0);
                uint32_t expected=x<8 && y<4 ? colours[(block+frame)%4] : 0xff000000;
                require(R32(d.data+y*d.pitch+x*4)==expected,0x100+y*16+x);
            }
        }
        require(R32(report+12)==0 && R32(report+8)>0,4);
        g_backend->Present(s.rt); g_backend->FrameWait();
    }
    g_backend->Flush(); g_backend->WaitFence(g_backend->Fence());
    // The changed colours lie between all three samples of the geometry
    // cache key. A matching lookup key must still validate mutable bytes.
    for (unsigned i=0; i<4; ++i) {
        float x=float(i*4);
        vertices[4*i]   = {x,0,.5f,1,colours[0]}; vertices[4*i+1] = {x+4,0,.5f,1,colours[0]};
        vertices[4*i+2] = {x+4,4,.5f,1,colours[0]}; vertices[4*i+3] = {x,4,.5f,1,colours[0]};
    }
    for (unsigned pass=0; pass<2; ++pass) {
        for (unsigned i=4; i<8; ++i) vertices[i].colour=colours[pass];
        std::memcpy(HostPtr(scratch+512,sizeof vertices),vertices,sizeof vertices);
        g_backend->Clear(s,0,nullptr,gpu::kClearTarget,0xff000000,1,0);
        g_backend->Draw(s,8,0,16,nullptr);
        gpu::TextureDesc d; require(gpu::Describe(surface,d),0x200);
        g_backend->Sync(d.data,gpu::TotalSize(d));
        require(R32(d.data+d.pitch+5*4)==colours[pass],0x201+pass);
    }
    // Exercise both an overwritten UP scratch buffer and a normal vertex
    // buffer with an intentional gap before the ninth segment.
    uint32_t buffer = NativeData(50 * sizeof(Vertex)), segment_data = scratch + 512;
    auto write_segment = [&](unsigned i, unsigned first) {
        float x = i & 1 ? 10.5f : 1.5f, y = float(i % 6) + .5f;
        Vertex endpoints[] = {{x,y,.5f,1,colours[i%4]}, {x+3,y,.5f,1,colours[i%4]}};
        std::memcpy(HostPtr(segment_data+first*sizeof(Vertex),sizeof endpoints),endpoints,sizeof endpoints);
    };
    std::array<uint32_t,128> reference;
    for (bool bound : {false, true}) {
        if (bound) {
            W32(vertex,0x01000001u); W32(vertex+4,buffer);
            segment_data = mem::VirtualFromPhysical(buffer);
        }
        auto first_vertex = [&](unsigned i) { return bound ? 2*(i+(i>=8)) : 0u; };
        if (bound) for (unsigned i=0; i<24; ++i) write_segment(i,first_vertex(i));
        for (unsigned pass = 0; pass < 2; ++pass) {
            g_backend->Clear(s,0,nullptr,gpu::kClearTarget,0xff000000,1,0);
            g_backend->WaitFence(g_backend->Fence());
            uint64_t first = ngb_test_unindexed_draws();
            for (unsigned i = 0; i < 24; ++i) {
                if (!bound) write_segment(i,0);
                s.simple[gpu::kMColorWriteEnable/4] = i < 12 ? 0x01010101 : 0x00010100;
                g_backend->Draw(s,i & 1 ? 2 : 4,first_vertex(i),2,nullptr);
                if (!pass) g_backend->WaitFence(g_backend->Fence());
            }
            g_backend->WaitFence(g_backend->Fence());
            uint64_t draws = ngb_test_unindexed_draws() - first;
            require(draws == (pass ? (bound ? 3u : 2u) : 24u), 0x210);
            gpu::TextureDesc d; require(gpu::Describe(surface,d),0x211);
            g_backend->Sync(d.data,gpu::TotalSize(d));
            unsigned painted = 0;
            for (unsigned y=0; y<8; ++y) for (unsigned x=0; x<16; ++x) {
                uint32_t pixel=R32(d.data+y*d.pitch+x*4);
                painted += (pixel & 0xffffff) != 0;
                if (bound || pass) require(reference[y*16+x]==pixel,0x300+y*16+x);
                else reference[y*16+x]=pixel;
            }
            require(painted > 0 && painted < reference.size(),0x212);
            std::fprintf(stderr,"[LINE-CONTRACT] bound=%d pass=%u draws=%llu painted=%u\n",bound,pass,(unsigned long long)draws,painted);
        }
    }
    ngb_contiguous_free(mem::VirtualFromPhysical(buffer));
    std::fprintf(stderr,"[SUBMISSION-CONTRACT-PASS] queued before present, no waits or resets, geometry lifetime, copy, visibility, slot reuse\n");
    // Keep this fixture's targets until device teardown. Reusing their guest
    // addresses in another fixture mixes independent readback expectations.
    return {surface,copy,scratch};
}
