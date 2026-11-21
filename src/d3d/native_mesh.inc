// Complete mesh submission's renderer boundary. Included after material:: and
// NativeMaterialEnabled. Unmodified game callbacks invalidate the owned state.
extern "C" { uint32_t ngb_native_mesh_enabled = 1; }

static bool NativeMeshEnabled() {
    if (!NativeMaterialEnabled()) return false;
    static const unsigned mode = [] {
        const char* v = std::getenv("NGB_NATIVE_MESH");
        return v && !std::strcmp(v, "ab") ? 2u : v && !std::strcmp(v, "0") ? 0u : 1u;
    }();
    unsigned phase = (native_frames / 8) & 3;
    return mode == 2 ? phase == 1 || phase == 2 : mode;
}

extern "C" void ngb_d3d_mesh_invalidate(void) { native_mesh_coherent = false; }
// The token lives on the current host/fiber stack. A callback or another guest
// worker must not inherit ownership of its caller's model traversal.
extern "C" unsigned ngb_d3d_model_suspend(void) {
    unsigned depth = native_model_depth;
    native_model_depth = 0; native_mesh_coherent = false;
    return depth;
}
extern "C" void ngb_d3d_model_resume(unsigned depth) {
    native_model_depth = depth; native_mesh_coherent = false;
}
extern "C" void ngb_d3d_model_scope(int enter) {
    native_mesh_coherent = false;
    if (enter) ++native_model_depth;
    else --native_model_depth;
}
extern "C" void ngb_d3d_model_world(uint32_t matrix) {
    W32(0x977bd4, matrix);
    const auto* p = static_cast<const uint32_t*>(HostPtr(matrix, 64));
    auto* d = static_cast<uint32_t*>(HostPtr(R32(kDevicePtr) + 0xde0, 64));
    // The original rep movsd copies forwards even for overlapping inputs.
    for (unsigned i = 0; i < 16; ++i) d[i] = p[i];
    W32(0x3d83d0, R32(0x3d83d0) | 0x200);
    std::memcpy(g_state.transforms[256].data(), d, 64);
    native_mesh_changed |= gpu::PreparedState::WorldMatrices;
}
extern "C" void ngb_d3d_mesh_scope(int enter) {
    if (!native_model_depth) native_mesh_coherent = false;
    if (enter) ++native_mesh_batches;
}
extern "C" int ngb_d3d_mesh_allowed(uint32_t address) {
    ++native_mesh_attempts;
    return ngb_native_mesh_enabled && NativeMeshEnabled() && R32(address + 8) <= 4;
}
extern "C" void ngb_d3d_mesh_fixed(uint32_t address) {
    NativeFlush(); NativeDiagScope diag(ND_STATE);
    material::Fixed<true>(address);
    ++material_batches;
}
extern "C" int ngb_d3d_mesh_texture(unsigned stage, uint32_t address) {
    if (stage >= 4) return 0;
    NativeFlush(); NativeDiagScope diag(ND_STATE);
    material::Texture<true>(stage, address);
    return 1;
}
extern "C" void ngb_d3d_mesh_simple(uint32_t cache, unsigned state, unsigned method, uint32_t value) {
    if (R32(cache) != value) NativeFlush();
    material::Tables<true> t;
    t.Simple(cache, state, method, value);
}
extern "C" void ngb_d3d_mesh_disable(unsigned stage) {
    material::Tables<true> t;
    t.Texture(stage, 0x9779a8, 12, 1, 0x800);
    t.Texture(stage, 0x9779b8, 16, 1, 0x800);
}
extern "C" void ngb_d3d_mesh_unbind(unsigned stage) {
    uint32_t cache = 0x977968 + stage * 4;
    if (!R32(cache)) return;
    W32(cache, 0);
    NativeFlush();
    NativeBind(R32(kNativeDevice + 0xf88 + stage * 4), 0);
    W32(kNativeDevice + 0xf88 + stage * 4, 0);
    g_state.textures[stage] = 0;
    native_mesh_changed |= gpu::PreparedState::Bindings | gpu::PreparedState::ResourceHeaders;
}
extern "C" void ngb_d3d_mesh_modulate(unsigned stage, uint32_t color) {
    material::Tables<true> t;
    t.Texture(stage, 0x9779b4, 15, 1, 0x800);
    t.Texture(stage, 0x9779a8, 12, 3, 0x800);
    t.Texture(stage, 0x9779c0, 18, 3, 0x800);
    t.Texture(stage, 0x9779c4, 19, 1, 0x800);
    t.Texture(stage, 0x9779b8, 16, 4, 0x800);
    if (R32(0x977920) != color) NativeFlush();
    t.Complex(0x977920, gpu::kRsTextureFactor, color);
}
extern "C" void ngb_d3d_mesh_draw(uint32_t address) {
    if (!R32(address + 0x1c)) return;
    NativeFlush();
    if (!native_mesh_coherent) {
        SyncDeferred();
        native_mesh_coherent = true;
        ++native_mesh_syncs;
    } else ++native_mesh_reused;
    static const bool verify = std::getenv("NGB_NATIVE_MESH_VERIFY") != nullptr;
    if (verify) {
        gpu::State saved = g_state;
        uint32_t changes = native_mesh_changed;
        SyncDeferred();
        if (saved.simple != g_state.simple || saved.rs != g_state.rs || saved.tss != g_state.tss ||
            saved.textures != g_state.textures || saved.palettes != g_state.palettes ||
            std::memcmp(saved.transforms.data(), g_state.transforms.data(), sizeof(saved.transforms)) ||
            std::memcmp(saved.vsc.data(), g_state.vsc.data(), sizeof(saved.vsc)) ||
            std::memcmp(saved.material.data(), g_state.material.data(), sizeof(saved.material)))
            ngb_stop("native mesh state differs from guest state", address);
        g_state = std::move(saved);
        native_mesh_changed = changes;
    }
    ++native_mesh_draws;
    uint32_t kind = R32(address + 0x10), data = R32(address + 0x14);
    // The game's screen-history controller owns bit 2 while the trail is active.
    // Its additive mesh layers come through this material boundary before Vulkan.
    gpu::CombatEffect effect = gpu::CombatEffect::None;
    if (g_state.simple[gpu::kMBlendEnable / 4] && g_state.simple[gpu::kMSrcBlend / 4] == 0x302 &&
        g_state.simple[gpu::kMDestBlend / 4] == 1 && CombatEffectsEnabled() && (R32(0xc0611c) & 4))
        effect = gpu::CombatEffect::Transparent;
    if (!kind) RunPushBuffer(data, true, effect);
    else {
        uint32_t count = R32(address + 0x18) / 2;
        uint32_t indices = kind == 1 ? R32(data + 4) + 12 :
            R32(R32(R32(address + 4) + 0x18) + 4) + data;
        if (indices) Draw(6, 0, count, static_cast<const uint8_t*>(HostPtr(indices, size_t(count) * 2)), true, effect);
    }
}
extern "C" void ngb_d3d_mesh_stats(uint64_t out[8]) {
    out[0] = native_frames; out[1] = ngb_native_mesh_enabled;
    out[2] = native_mesh_attempts; out[3] = native_mesh_batches;
    out[4] = native_mesh_draws; out[5] = native_mesh_syncs; out[6] = native_mesh_reused;
    out[7] = native_completed_draws;
    native_mesh_attempts = native_mesh_batches = native_mesh_draws = native_mesh_syncs = native_mesh_reused = 0;
    ngb_native_mesh_enabled = NativeMeshEnabled();
}
