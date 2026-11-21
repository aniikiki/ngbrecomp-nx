extern "C" void ngb_test_submission_counts(uint64_t*);

static std::array<uint32_t,3> NativeSubmissionContract() {
    auto require = [](bool okay, unsigned detail) {
        if (!okay) ngb_stop("native submission contract failed", detail);
    };
    const char* samples = std::getenv("NGB_REPLAY_MSAA");
    bool multisampled = samples && std::atoi(samples) > 1;
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
                unsigned block=(x>=4 ? 1 : 0)+(y>=2 ? 2 : 0);
                uint32_t expected=x<8 && y<4 ? colours[(block+frame)%4] : 0xff000000;
                require(R32(d.data+y*d.pitch+x*4)==expected,0x100+y*16+x);
            }
        }
        require(R32(report+12)==0 && R32(report+8)>0,4);
        g_backend->Present(s.rt); g_backend->FrameWait();
    }
    g_backend->Flush(); g_backend->WaitFence(g_backend->Fence());
    std::fprintf(stderr,"[SUBMISSION-CONTRACT-PASS] queued before present, no waits or resets, geometry lifetime, copy, visibility, slot reuse\n");
    // Keep this fixture's targets until device teardown. Reusing their guest
    // addresses in another fixture mixes independent readback expectations.
    return {surface,copy,scratch};
}
