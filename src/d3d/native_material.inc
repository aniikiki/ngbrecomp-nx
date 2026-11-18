// Included by hle.cpp after native_device.inc. This is the title's material
// submission (0030B7E0 + 0030BA30), not another implementation of the XDK.
// Keep the title's cache coherent: effects also inspect and update it inline.
namespace material {
constexpr uint32_t cache_base = 0x9776c8;

template<bool Prepared = false> struct Tables {
    uint32_t* cache = static_cast<uint32_t*>(HostPtr(cache_base, 0x520));
    uint32_t* rs = static_cast<uint32_t*>(HostPtr(kRenderState, 166 * 4));
    uint32_t* ts = static_cast<uint32_t*>(HostPtr(kTextureState, 4 * 128));
    uint32_t& dirty = *static_cast<uint32_t*>(HostPtr(0x3d83d0, 4));
    uint32_t& Cached(uint32_t address) { return cache[(address - cache_base) / 4]; }
    void Deferred(uint32_t address, unsigned state, uint32_t value, uint32_t flags) {
        auto& old = Cached(address);
        if (old == value) return;
        old = value; rs[state] = value; dirty |= flags;
        if constexpr (Prepared) {
            native_mesh_changed |= gpu::PreparedState::Bindings;
            if (native_mesh_coherent) g_state.rs[state] = value;
        }
    }
    void Simple(uint32_t address, unsigned state, unsigned method, uint32_t value) {
        auto& old = Cached(address);
        if (old == value) return;
        old = value; rs[state] = value;
        g_state.simple[method / 4] = value;
        if constexpr (Prepared) native_mesh_changed |= gpu::PreparedState::Simple;
    }
    void Complex(uint32_t address, unsigned state, uint32_t value) {
        auto& old = Cached(address);
        if (old == value) return;
        old = value; rs[state] = value; g_state.rs[state] = value;
        if constexpr (Prepared) native_mesh_changed |= gpu::PreparedState::Bindings;
    }
    void Texture(unsigned stage, uint32_t address, unsigned state, uint32_t value, uint32_t flags) {
        auto& old = Cached(address + stage * 128);
        if (old == value) return;
        old = value; ts[stage * 32 + state] = value; dirty |= flags;
        if constexpr (Prepared) {
            native_mesh_changed |= gpu::PreparedState::Bindings;
            if (native_mesh_coherent && stage < 4) g_state.tss[stage][state] = value;
        }
    }
};

template<bool Prepared = false> void Fixed(uint32_t address) {
    // Binding can release the previous resource and enter the guest allocator.
    // Acquire ordinary-RAM views only after that boundary, never across it.
    uint32_t vertex = R32(address + 4), shader = R32(vertex);
    if (R32(0x9776c8) != shader) {
        W32(0x9776c8, shader); W32(kNativeDevice + 0x794, shader);
        g_state.vs_handle = shader; g_state.vs.reset();
        if constexpr (Prepared) native_mesh_changed |= gpu::PreparedState::Vertex;
        if (shader & 1) {
            auto it = g_vs.find(shader);
            if (it != g_vs.end()) g_state.vs = it->second;
        }
    }
    uint32_t stride = R32(vertex + 0x10), buffer = R32(vertex + 8);
    uint32_t previous_buffer = R32(0x3d93b0);
    NativeBind(previous_buffer, buffer);
    if constexpr (Prepared) {
        if (previous_buffer != buffer) native_mesh_changed |= gpu::PreparedState::ResourceHeaders;
    }
    W32(0x3d93b0, buffer); W32(0x3d93a8, stride);
    if constexpr (Prepared) {
        if (g_state.streams[0].vb != buffer || g_state.streams[0].stride != stride)
            native_mesh_changed |= gpu::PreparedState::Bindings;
    }
    g_state.streams[0] = {buffer, stride};

    Tables<Prepared> t;
    const auto* m = static_cast<const uint32_t*>(HostPtr(address, 0x60));
    t.Deferred(0x977868, 102, m[8], 0x1200);
    t.Deferred(0x977840, 92, m[9] && R32(0x44b3c0), 0x2000);
    t.Simple(0x9777bc, 59, 0x304, m[10]);
    t.Simple(0x9777c4, 61, 0x340, 0);
    t.Complex(0x97791c, 147, m[12]);
    t.Complex(0x9778f4, 137, m[13]);
    t.Simple(0x9777c8, 62, 0x344, m[14]);
    t.Simple(0x9777cc, 63, 0x348, m[15]);
    t.Complex(0x977910, 144, m[16]);
    t.Simple(0x9777ec, 71, 0x368, m[17]);
    t.Complex(0x97790c, 143, 1);
    t.Simple(0x9777d0, 64, 0x35c, m[11]);
    if (!m[8]) return;

    const auto* lighting = static_cast<const float*>(HostPtr(address + 0x60, 0x50));
    const auto* previous = reinterpret_cast<const float*>(&t.Cached(0x977b78));
    bool same = true;
    // The title compares floats, so signed zero is equal and NaN is different.
    for (unsigned i = 0; i < 17; ++i) same &= previous[i] == lighting[i];
    if (!same) {
        std::memcpy(&t.Cached(0x977b78), lighting, 17 * 4);
        std::memcpy(HostPtr(R32(kDevicePtr) + 0xf00, 17 * 4), lighting, 17 * 4);
        if constexpr (Prepared) {
            if (native_mesh_coherent) std::memcpy(g_state.material.data(), lighting, 17 * 4);
            native_mesh_changed |= gpu::PreparedState::Material;
        }
        t.dirty |= 0x9000;
    }
    const auto* l = reinterpret_cast<const uint32_t*>(lighting);
    t.Deferred(0x97786c, 103, l[17], 0x3000);
    t.Deferred(0x97788c, 111, l[18], 0x1000);
    t.Deferred(0x977890, 112, l[19], 0x1000);
}

template<bool Prepared = false> void Texture(unsigned stage, uint32_t address) {
    uint32_t handle = R32(address + 4), cache = 0x977968 + stage * 4;
    if (R32(cache) != handle) {
        W32(cache, handle);
        NativeBind(R32(kNativeDevice + 0xf88 + stage * 4), handle);
        W32(kNativeDevice + 0xf88 + stage * 4, handle);
        g_state.textures[stage] = handle;
        if constexpr (Prepared)
            native_mesh_changed |= gpu::PreparedState::Bindings | gpu::PreparedState::ResourceHeaders;
    }
    Tables<Prepared> t;
    const auto* m = static_cast<const uint32_t*>(HostPtr(address, 0x40));
    for (unsigned i = 0; i < 8; ++i)
        t.Texture(stage, 0x9779a8 + i * 4, 12 + i, m[4 + i], 0x800);
    t.Texture(stage, 0x977984, 3, 2, 1u << stage);
    t.Texture(stage, 0x977988, 4, 2, 1u << stage);
    t.Texture(stage, 0x97798c, 5, 1, 1u << stage);
    t.Texture(stage, 0x977990, 6, m[12], 1u << stage);
    t.Texture(stage, 0x9779cc, 21, m[14], 0x400);
    auto& coords = t.Cached(0x9779e8 + stage * 128);
    if (coords != m[15]) {
        coords = m[15]; t.ts[stage * 32 + 28] = m[15];
        g_state.tss[stage][gpu::kTssTexCoordIndex] = m[15];
        if constexpr (Prepared) native_mesh_changed |= gpu::PreparedState::Bindings;
    }
    unsigned transform = stage + 2;
    auto& matrix = t.Cached(0x977bbc + transform * 4);
    if (m[15] && matrix != 0x44b3d0) {
        matrix = 0x44b3d0;
        const void* value = HostPtr(0x44b3d0, 64);
        std::memcpy(HostPtr(kNativeDevice + 0xc60 + transform * 64, 64), value, 64);
        std::memcpy(g_state.transforms[transform + 14].data(), value, 64);
        if constexpr (Prepared) native_mesh_changed |= gpu::PreparedState::TextureMatrices;
    }
}

bool Submit(uint32_t address) {
    // A material is bounded by four texture stages. Unsupported/corrupt layouts
    // stay on the existing path before any state or reference count is changed.
    unsigned stages = R32(address + 8);
    if (stages > 4) return false;
    NativeFlush();
    NativeDiagScope diag(ND_STATE);
    Fixed(address);
    uint32_t texture = address + 0x60 + (R32(address + 0x20) ? 0x50 : 0);
    for (unsigned stage = 0; stage < stages; ++stage, texture += 0x40)
        Texture(stage, texture);
    return true;
}
} // namespace material
