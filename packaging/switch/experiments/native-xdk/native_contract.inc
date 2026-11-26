// Included only by the headless contract-test executable, after native_device.inc.
extern "C" unsigned ngb_native_test_callback_hits;
#include "native_lifetime_contract.inc"
#include "native_header_contract.inc"
#include "native_effect_contract.inc"
#include "native_submission_contract.inc"
#include "native_shader_contract.inc"

static void NativeDrawStateContract() {
    auto saved = g_state;
    uint32_t pending = native_mesh_changed;
    SyncDeferred();
    // With native meshes disabled, SyncDeferred also hydrates the simple method table.
    constexpr uint32_t deferred_groups = ~(Groups::Simple | Groups::DepthClip);
    for (unsigned stage = 0; stage < 4; ++stage) {
        const uint32_t addr = kTextureState + stage * 128 + 4 * gpu::kTssColorOp;
        uint32_t previous = R32(addr);
        native_mesh_changed = 0;
        W32(addr, previous ^ 1u);
        SyncDeferred();
        if (g_state.tss[stage][gpu::kTssColorOp] != (previous ^ 1u) ||
            (native_mesh_changed & deferred_groups) != (Groups::TextureStage(stage) | Groups::ResourceHeaders))
            ngb_stop("inline texture stage was not isolated", stage);
        W32(addr, previous);
        SyncDeferred();
    }
    const uint32_t addr = kRenderState + 4 * gpu::kRsFogColor;
    uint32_t previous = R32(addr);
    native_mesh_changed = 0;
    W32(addr, previous ^ 1u);
    SyncDeferred();
    if (g_state.rs[gpu::kRsFogColor] != (previous ^ 1u) ||
        (native_mesh_changed & deferred_groups) != (Groups::RenderStates | Groups::ResourceHeaders))
        ngb_stop("inline render state was not isolated", addr);
    W32(addr, previous);
    SyncDeferred();
    auto old_stream = g_state.streams[0];
    native_mesh_changed = 0;
    SetDrawStream(0, old_stream.vb, old_stream.stride ^ 4u);
    if (native_mesh_changed != Groups::Streams)
        ngb_stop("temporary stream change was not recorded", 0);
    native_mesh_changed = 0;
    SetDrawStream(0, old_stream.vb, old_stream.stride ^ 4u);
    if (native_mesh_changed) ngb_stop("identical stream marked dirty", 0);
    SetDrawStream(0, old_stream.vb, old_stream.stride);
    if (native_mesh_changed != Groups::Streams)
        ngb_stop("stream restoration was not recorded", 0);
    native_mesh_changed = 0;
    uint32_t other = old_stream.vb ? 0 : kNativeDevice;
    SetDrawStream(0, other, old_stream.stride);
    if (native_mesh_changed != (Groups::Streams | Groups::HeaderBindings | Groups::HeaderWrite(other)))
        ngb_stop("stream rebinding was not recorded", other);
    g_state = std::move(saved);
    native_mesh_changed = pending;
}

extern "C" void ngb_d3d_native_test(void) {
    auto require = [](bool okay, uint32_t detail) {
        if (!okay) ngb_stop("native graphics contract failed", detail);
    };
    uint32_t scratch = NativePool(4096), stack = scratch + 512;
    auto call = [&](int fn, uint32_t eax, uint32_t ebx, std::initializer_list<uint32_t> args) {
        uint32_t regs[8]{}; regs[EAX] = eax; regs[EBX] = ebx; regs[ESP] = stack;
        unsigned at = 4; for (uint32_t arg : args) { W32(stack + at, arg); at += 4; }
        NativeCall(fn, Call{regs});
        require(regs[ESP] == stack + at, 0x1000 + fn);
        return regs[EAX];
    };

    // Mapping aliases are live guest data, not a table of cached results.
    auto saved_simple=g_state.simple;
    std::array<uint32_t,gpu::kRsDeferredFirst> saved_states;
    std::memcpy(saved_states.data(),HostPtr(kRenderState,sizeof saved_states),sizeof saved_states);
    uint32_t encoded_a=R32(kSimpleEncode+4),encoded_b=R32(kSimpleEncode+8);
    W32(kSimpleEncode+4,0x403fc);W32(kSimpleEncode+8,0x403fc);
    native_simple_ready = false; // this fixture deliberately changes the otherwise immutable table
    NativeSimple(0x3fc,0x13579bdf);
    require(R32(kRenderState+4)==0x13579bdf && R32(kRenderState+8)==0x13579bdf &&
            g_state.simple[0x3fc/4]==0x13579bdf,19);
    W32(kSimpleEncode+4,encoded_a);W32(kSimpleEncode+8,encoded_b);
    native_simple_ready = false;
    std::memcpy(HostPtr(kRenderState,sizeof saved_states),saved_states.data(),sizeof saved_states);
    g_state.simple=saved_simple;
    NativeShaderContract();
    NativeVertexConstantContract();
    NativeDrawStateContract();
    NativeEffectContract();
    NativeBillboardContract();
    NativeCombatContract();
    NativeShadowContract();
    auto submission_resources = NativeSubmissionContract();

    // NGB inlines palette unbinding: changing the guest fields must take effect
    // even though no SetPalette hook runs. Rebinding must not decrement twice.
    uint32_t palette = scratch + 64;
    W32(palette, 0x00830001); W32(palette + 4, scratch + 1024);
    call(D3DF_D3DDevice_SetPalette, 0, 0, {palette});
    require(R32(kNativeDevice + 0xf98) == palette && R32(palette) == 0x008b0001, 1);
    W32(palette, R32(palette) - 0x80000); W32(kNativeDevice + 0xf98, 0);
    SyncDeferred(); require(g_state.palettes[0] == 0, 2);
    call(D3DF_D3DDevice_SetPalette, 0, 0, {palette});
    call(D3DF_D3DDevice_SetPalette, 0, 0, {0});
    require(R32(palette) == 0x00830001, 3);

    // A bound surface keeps both its parent texture and its data alive after
    // the caller releases its public references.
    uint32_t texture = NativeHeader(20);
    uint32_t bytes = NativeTextureHeader(8, 4, 1, 1, 6, 0, false, false, texture + 12, texture + 16);
    W32(texture, 0x01040001); W32(texture + 4, NativeData(bytes));
    uint32_t regs[8]{}; regs[EAX] = texture; regs[ESP] = stack; W32(stack + 4, 0);
    NativeHelper(0x3c8580, Call{regs}); uint32_t view = regs[EAX];
    require(R32(texture) == 0x01040002 && R32(view + 20) == texture && regs[ESP] == stack + 8, 4);
    NativeBind(0, view); NativeRelease(texture); NativeRelease(view);
    require(R32(texture) == 0x010c0000 && R32(view) == 0x010d0000, 5);
    NativeBind(view, 0);

    // Check actual Vulkan results in guest memory, including pitch padding,
    // swizzled addressing, packed 16-bit colour and separate depth/stencil.
    for (uint32_t format : {0x12u, 0x06u, 0x11u}) {
        uint32_t surface = NativeCreateSurface(8, 4, format);
        gpu::State s = g_state; s.rt = SurfaceOf(surface); s.zs = {};
        s.viewport = {0, 0, 8, 4, 0, 1}; s.scissor_count = 0;
        g_backend->Clear(s, 0, nullptr, gpu::kClearTarget, 0xff1a82e3, 1, 0);
        int32_t rectangle[] = {2, 1, 6, 3};
        g_backend->Clear(s, 1, reinterpret_cast<uint8_t*>(rectangle), gpu::kClearTarget, 0xfffa480c, 1, 0);
        gpu::TextureDesc d; require(gpu::Describe(surface, d), 6);
        g_backend->Sync(d.data, gpu::TotalSize(d));
        unsigned bpp = gpu::Format(format).bits / 8;
        for (unsigned y = 0; y < 4; ++y) for (unsigned x = 0; x < 8; ++x) {
            uint8_t expected[4]; uint32_t colour = x >= 2 && x < 6 && y >= 1 && y < 3 ? 0xfffa480c : 0xff1a82e3;
            gpu::EncodeRenderPixel(format, colour, 0, 0, expected);
            uint32_t offset = gpu::RenderPixelOffset(x, y, 8, 4, bpp, d.pitch, d.linear);
            require(!std::memcmp(HostPtr(d.data + offset, bpp), expected, bpp), 0x2000 + format * 32 + y * 8 + x);
        }
        if (d.linear) require(R32(d.data + 8 * bpp) == 0, 7);
        NativeRelease(surface);
    }
    uint32_t colour = NativeCreateSurface(8, 4, 0x12), depth = NativeCreateSurface(8, 4, 0x2e);
    gpu::State s = g_state; s.rt = SurfaceOf(colour); s.zs = SurfaceOf(depth);
    s.viewport = {0, 0, 8, 4, 0, 1}; s.scissor_count = 0;
    g_backend->Clear(s, 0, nullptr, gpu::kClearZ | gpu::kClearStencil, 0, .25f, 0x53);
    g_backend->Sync(R32(depth + 4), 256);
    require(R32(R32(depth + 4) | 0x80000000u) == 0x40000053, 8);
    g_backend->Clear(s, 0, nullptr, gpu::kClearStencil, 0, 0, 0x67);
    g_backend->Sync(R32(depth + 4), 256);
    require(R32(R32(depth + 4) | 0x80000000u) == 0x40000067, 0x501);
    g_backend->Clear(s, 0, nullptr, gpu::kClearZ, 0, .5f, 0);
    g_backend->Sync(R32(depth + 4), 256);
    require(R32(R32(depth + 4) | 0x80000000u) == 0x80000067, 0x502);
    uint32_t fence = g_backend->Fence(); g_backend->WaitFence(fence);
    require(!g_backend->FencePending(fence) && !g_backend->Busy(depth), 9);

    // A GPU visibility callback must wait for the report as well as for the
    // recorded batch. The callback's guest ABI is exercised by the runtime
    // allocator calls above; here a test-only wrapper checks its argument.
    struct Vertex { float x, y, z, w; uint32_t colour; };
    Vertex triangle[] = {{0,0,.5f,1,~0u},{8,0,.5f,1,~0u},{0,4,.5f,1,~0u}};
    std::memcpy(HostPtr(scratch + 1024, sizeof triangle), triangle, sizeof triangle);
    uint32_t vertex_header = scratch + 96;
    W32(vertex_header, 0x80000001); W32(vertex_header + 4, scratch + 1024);
    s.zs = {}; s.vs_handle = 0x44; s.vs.reset(); s.ps.reset(); s.textures.fill(0); s.palettes.fill(0);
    s.streams[0] = {vertex_header, sizeof(Vertex)};
    s.rs[gpu::kRsLighting] = s.rs[gpu::kRsCullMode] = s.rs[gpu::kRsZEnable] = 0;
    g_backend->VisibilityBegin(); g_backend->Draw(s, 4, 0, 3, nullptr);
    call(D3DF_D3DDevice_EndVisibilityTest, 17, 0, {});
    uint32_t report = native_last_report;
    native_callbacks.push_back({0xfffffff0u, 0x12345678, g_backend->Fence(), report});
    g_backend->Flush(); g_backend->WaitFence(g_backend->Fence()); NativePoll();
    require(R32(report + 12) == 0 && R32(report + 8) > 0 && ngb_native_test_callback_hits == 1, 14);

    g_state.scissor_count = 1;
    call(D3DF_D3DDevice_SetRenderTarget, 0, 0, {colour, depth});
    require(g_state.scissor_count == 0 && R32(kNativeDevice + 0xee8) == 8, 10);
    call(D3DF_D3DDevice_SetRenderTarget, 0, 0, {native_back, native_depth});
    NativeRelease(colour); NativeRelease(depth);
    call(D3DF_D3DDevice_SetStreamSource, 3, 0, {28});
    require(R32(0x3d93a8 + 36) == 28, 11);
    uint32_t empty_push = scratch + 128, push_data = NativeData(64);
    W32(empty_push, 0x20001); W32(empty_push + 4, push_data); W32(empty_push + 12, 64);
    call(D3DF_D3DDevice_RunPushBuffer, 0, 0, {empty_push,0});
    require(ngb_contiguous_free(push_data | 0x80000000u), 18);
    call(D3DF_D3DDevice_SetScreenSpaceOffset, 0, 0, {0,0});
    require(R32(kNativeDevice + 0xef8) == 0x3f080000 && g_state.ss_offset_x == 0, 15);
    call(D3DF_D3DDevice_SetShaderConstantMode, 0x11, 0, {});
    require(R32(kNativeDevice + 0x1928) == 1 && (R32(kNativeDevice + 8) & 0x200), 16);
    NativeLightEnable(300, true); require(R32(kNativeDevice + 0x7a8) == 512, 17);
    uint32_t light = NativeLight(300), slot = R32(light + 0x8c), desc = scratch + 2048;
    W32(light + 0x68, 0);
    auto revision = g_state.lights_revision;
    W32(stack + 4, 1);
    uint32_t cursor = R32(kNativeDevice);
    W32(kNativeDevice, cursor + 4);
    require(!ngb_d3d_light_enable_ready(300, stack) && R32(light + 0x68) == 0, 23);
    W32(kNativeDevice, cursor);
    require(!ngb_d3d_light_enable_ready(512, stack) && ngb_d3d_light_enable_ready(300, stack), 24);
    require(R32(light + 0x68) == 4 && g_state.lights_revision == revision, 19);
    std::memcpy(HostPtr(desc, 104), HostPtr(light, 104), 104);
    NativeSetLight(300, desc);
    require(g_state.lights_revision == revision && R32(light + 0x68) == 7, 20);
    W32(desc + 64, 0x80000000u);
    W32(desc + 8, 0x3e800000);
    NativeSetLight(300, desc);
    require(g_state.lights_revision != revision && R32(light + 0x6c) == 0 &&
            !std::memcmp(g_state.lights[slot].data(), HostPtr(desc, 104), 104), 21);
    NativeLightEnable(300, false);
    revision = g_state.lights_revision;
    W32(light + 0x68, 0);
    NativeLightEnable(300, false);
    require(g_state.lights_revision == revision && R32(light + 0x68) == 4 &&
            (g_state.light_enable & (1u << slot)) == 0, 22);
    W32(stack + 4, 300); W32(stack + 8, desc);
    W32(kNativeDevice, cursor + 4);
    require(!ngb_d3d_set_light_ready(stack) && !ngb_d3d_lights_already_disabled(6), 0x7101);
    W32(kNativeDevice, cursor);
    W32(stack + 4, 512);
    require(!ngb_d3d_set_light_ready(stack), 0x7102);
    W32(stack + 4, 300);
    require(ngb_d3d_set_light_ready(stack) && !std::memcmp(HostPtr(light, 104), HostPtr(desc, 104), 104) &&
            R32(light + 0x68) == 7 && !R32(light + 0x6c), 0x7103);
    NativeLightEnable(6, false); NativeLightEnable(7, false);
    require(ngb_d3d_lights_already_disabled(6), 0x7104);
    W32(NativeLight(7) + 0x68, 0);
    require(!ngb_d3d_lights_already_disabled(6) && !R32(NativeLight(7) + 0x68), 0x7105);
    NativeLightEnable(7, true);
    require(!ngb_d3d_lights_already_disabled(6), 0x7106);

    W32(scratch, 640); W32(scratch + 4, 480); W32(scratch + 8, 0x12);
    W32(scratch + 32, 1); W32(scratch + 36, 0x2e);
    NativeReset(scratch);
    require(g_state.viewport.w == 640 && g_state.viewport.h == 480 && R32(kDevicePtr) == kNativeDevice, 12);
    call(D3DF_D3DDevice_SetPalette, 0, 0, {palette});
    W32(palette, R32(palette) - 0x80000); W32(kNativeDevice + 0xf98, 0);
    NativeDestroyDevice(); require(!native_push && !R32(kDevicePtr) && !g_backend, 13);
    NativeRelease(submission_resources[0]); NativeRelease(submission_resources[1]);
    ngb_graphics_pool_free(submission_resources[2]);
    NativeLifetimeContract(scratch);
    NativeHeaderContract();
    NativePresentContract();
    ngb_graphics_pool_free(scratch);
    std::fprintf(stderr, "[CONTRACT-PASS] palette-inline parent-lifetime colour-linear colour-swizzled colour-565 depth-stencil fences visibility callback viewport reset destroy\n");
}
