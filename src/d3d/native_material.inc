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
            native_mesh_changed |= gpu::PreparedState::RenderStates;
            if (native_mesh_coherent) g_state.rs[state] = value;
        }
    }
    void Simple(uint32_t address, unsigned state, unsigned method, uint32_t value) {
        auto& old = Cached(address);
        if (old == value) return;
        old = value; rs[state] = value;
        g_state.simple[method / 4] = value;
        native_mesh_changed |= gpu::PreparedState::SimpleMethod(method);
        RememberSimpleWrite(state, method, value);
    }
    void Complex(uint32_t address, unsigned state, uint32_t value) {
        auto& old = Cached(address);
        if (old == value) return;
        old = value; rs[state] = value; g_state.rs[state] = value;
        native_mesh_changed |= state == gpu::kRsTextureFactor ? gpu::PreparedState::InstanceValues
                                                              : gpu::PreparedState::RenderStates;
    }
    void Texture(unsigned stage, uint32_t address, unsigned state, uint32_t value, uint32_t flags) {
        auto& old = Cached(address + stage * 128);
        if (old == value) return;
        old = value; ts[stage * 32 + state] = value; dirty |= flags;
        if constexpr (Prepared) {
            native_mesh_changed |= gpu::PreparedState::TextureStage(stage);
            if (native_mesh_coherent && stage < 4) g_state.tss[stage][state] = value;
        }
    }
};

static void BindVertex(uint32_t address) {
    // Binding can release the previous resource and enter the guest allocator.
    // Acquire ordinary-RAM views only after that boundary, never across it.
    uint32_t vertex[5];
    std::memcpy(vertex, ReadPtr(R32(address + 4), sizeof vertex), sizeof vertex);
    uint32_t shader = vertex[0], buffer = vertex[2], stride = vertex[4];
    if (R32(0x9776c8) != shader) {
        W32(0x9776c8, shader); W32(kNativeDevice + 0x794, shader);
        g_state.vs_handle = shader; g_state.vs.reset();
        native_mesh_changed |= gpu::PreparedState::Vertex;
        if (shader & 1) {
            auto it = g_vs.find(shader);
            if (it != g_vs.end()) g_state.vs = it->second;
        }
    }
    uint32_t previous_buffer = R32(0x3d93b0);
    if (previous_buffer != buffer) {
        NativeBind(previous_buffer, buffer);
        W32(0x3d93b0, buffer);
    }
    W32(0x3d93a8, stride);
    SetDrawStream(0, buffer, stride);
}

template<bool Prepared> void WriteFixed(Tables<Prepared>& t, const uint32_t* m, uint32_t fog) {
    t.Deferred(0x977868, 102, m[8], 0x1200);
    t.Deferred(0x977840, 92, fog, 0x2000);
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
}

// Effects can edit either the descriptor or the title's active registers
// between two instances. Compare the contiguous groups in register order.
static bool FixedBound(const uint32_t* m, const uint32_t* cache, uint32_t fog) {
    auto reg = [&](uint32_t address) -> const uint32_t& { return cache[(address - cache_base) / 4]; };
    const uint32_t blend[] = {0, m[14], m[15], m[11]};
    const uint32_t depth_stencil[] = {1, m[16]};
    return !std::memcmp(&reg(0x9777c4), blend, sizeof blend) &&
        !std::memcmp(&reg(0x97790c), depth_stencil, sizeof depth_stencil) &&
        reg(0x977868) == m[8] && reg(0x977840) == fog && reg(0x9777bc) == m[10] &&
        reg(0x97791c) == m[12] && reg(0x9778f4) == m[13] && reg(0x9777ec) == m[17];
}

template<bool Prepared> void FixedParameters(uint32_t address) {
    const auto* m = static_cast<const uint32_t*>(ReadPtr(address, 0x60));
    const uint32_t fog = m[9] && R32(0x44b3c0);
    const auto* cache = static_cast<const uint32_t*>(ReadPtr(cache_base, 0x977920 - cache_base));
    const bool changed = !FixedBound(m, cache, fog);
    if (!changed && !m[8]) return;
    Tables<Prepared> t;
    if (changed) WriteFixed(t, m, fog);
    if (!m[8]) return;

    const auto* lighting = static_cast<const float*>(ReadPtr(address + 0x60, 0x50));
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

template<bool Prepared = false> void Fixed(uint32_t address) {
    BindVertex(address);
    FixedParameters<Prepared>(address);
}

template<bool Prepared = false> void Texture(unsigned stage, uint32_t address) {
    uint32_t handle = R32(address + 4), cache = 0x977968 + stage * 4;
    if (R32(cache) != handle) {
        W32(cache, handle);
        NativeBind(R32(kNativeDevice + 0xf88 + stage * 4), handle);
        W32(kNativeDevice + 0xf88 + stage * 4, handle);
        g_state.textures[stage] = handle;
        native_mesh_changed |= gpu::PreparedState::TexturesAndPalettes | gpu::PreparedState::HeaderBindings | gpu::PreparedState::HeaderWrite(handle);
    }
    const auto* m = static_cast<const uint32_t*>(ReadPtr(address, 0x40));
    // Animated frames often change only the binding above. Compare the live
    // title registers before mapping the tables containing the write targets.
    constexpr uint32_t filter_base = 0x977984;
    const auto* cached = static_cast<const uint32_t*>(HostPtr(filter_base + stage * 128, 0x68));
    const uint32_t filters[] = {2, 2, 1, m[12]};
    const bool combiner_changed = std::memcmp(cached + (0x9779a8 - filter_base) / 4, m + 4, 8 * sizeof(uint32_t)) != 0;
    const bool filters_changed = std::memcmp(cached, filters, sizeof filters) != 0;
    const bool load_matrix = m[15] && R32(0x977bc4 + stage * 4) != 0x44b3d0;
    if (!combiner_changed && !filters_changed && cached[(0x9779cc - filter_base) / 4] == m[14] &&
        cached[(0x9779e8 - filter_base) / 4] == m[15] && !load_matrix) return;
    Tables<Prepared> t;
    if (combiner_changed) {
        for (unsigned i = 0; i < 8; ++i)
            t.Texture(stage, 0x9779a8 + i * 4, 12 + i, m[4 + i], 0x800);
    }
    if (filters_changed) {
        for (unsigned i = 0; i < 4; ++i) t.Texture(stage, 0x977984 + i * 4, 3 + i, filters[i], 1u << stage);
    }
    t.Texture(stage, 0x9779cc, 21, m[14], 0x400);
    auto& coords = t.Cached(0x9779e8 + stage * 128);
    if (coords != m[15]) {
        coords = m[15]; t.ts[stage * 32 + 28] = m[15];
        g_state.tss[stage][gpu::kTssTexCoordIndex] = m[15];
        native_mesh_changed |= gpu::PreparedState::TextureStage(stage);
    }
    unsigned transform = stage + 2;
    if (load_matrix) {
        t.Cached(0x977bbc + transform * 4) = 0x44b3d0;
        const void* value = HostPtr(0x44b3d0, 64);
        std::memcpy(HostPtr(kNativeDevice + 0xc60 + transform * 64, 64), value, 64);
        std::memcpy(g_state.transforms[transform + 14].data(), value, 64);
        native_mesh_changed |= gpu::PreparedState::TextureMatrices;
    }
}

// The active material is already in the title's register cache. Test the
// complete one-stage layout in one visit, including live descriptor edits.
// Geometry, texture backing, world and instance alpha are still read per draw.
bool PrepareMesh(uint32_t address, uint32_t return_slot) {
    BindVertex(address);
    // Binding can release the previous resource and call back into the title.
    // Only borrow this view once the bind completes.
    const auto* m = (address && !(address & 3))
        ? static_cast<const uint32_t*>(kernel::ReadPage(address, 0xa0)) : nullptr;
    if (!m || m[2] != 1 || m[8] || (m[20] & 255) || m[39]) {
        FixedParameters<true>(address);
        return false;
    }
    const auto* cache = static_cast<const uint32_t*>(ReadPtr(cache_base, 0x9779ec - cache_base));
    const uint32_t fog = m[9] && R32(0x44b3c0);
    if (!FixedBound(m, cache, fog)) {
        // A descriptor in the title's register area can alias the writes
        // below. The ordinary routine observes each change in guest order.
        if ((address & 0x7fffffffu) < cache_base + 0x520) {
            FixedParameters<true>(address);
            return false;
        }
        Tables<true> t;
        WriteFixed(t, m, fog);
    }
    // The emulated call stores a return address before reading the texture.
    const uint32_t slot = return_slot & 0x7fffffffu;
    if ((slot & 3) || slot - (address & 0x7fffffffu) < 0xa0 || slot - cache_base < 0x520) return false;
    const uint32_t* stage = m + 0x60 / 4;
    auto reg = [&](uint32_t va) -> const uint32_t& { return cache[(va - cache_base) / 4]; };
    if (reg(0x977968) != stage[1]) return false;
    const uint32_t filters[] = {2, 2, 1, stage[12]};
    return !std::memcmp(&reg(0x9779a8), stage + 4, 8 * sizeof(uint32_t)) &&
        !std::memcmp(&reg(0x977984), filters, sizeof filters) &&
        reg(0x9779cc) == stage[14] && reg(0x9779e8) == 0;
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
