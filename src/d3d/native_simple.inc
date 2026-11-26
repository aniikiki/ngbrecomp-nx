// The XBE's SimpleRenderStateEncode table is immutable. Build its reverse
// index once per device instead of scanning 92 encodings for every setter.
// Preserve duplicate encodings and the original ordering during hydration.
struct NativeSimpleTable {
    static constexpr uint8_t end = 255;
    static_assert(gpu::kRsDeferredFirst < end);
    std::array<uint8_t, 2048> first;
    std::array<uint8_t, gpu::kRsDeferredFirst> next;
    struct Copy { uint16_t method; uint8_t state; };
    std::array<Copy, gpu::kRsDeferredFirst> copies;
    std::array<uint32_t, gpu::kRsDeferredFirst> last_input{};
    std::array<uint32_t, 64> last_output{}; // methods 0x300..0x3fc
    uint32_t last_clip{};
    bool hydrated = false;
    unsigned count = 0;
    void Build() {
        first.fill(end); count = 0; hydrated = false;
        std::array<uint16_t, gpu::kRsDeferredFirst> methods;
        for (unsigned i = 0; i < methods.size(); ++i) {
            unsigned method = R32(kSimpleEncode + i * 4) & 0x1ffc;
            methods[i] = method >> 2;
            if ((method >= 0x300 && method < 0x400) || method == 0x1d78)
                copies[count++] = {uint16_t(method >> 2), uint8_t(i)};
        }
        for (unsigned i = methods.size(); i--;) {
            next[i] = first[methods[i]];
            first[methods[i]] = uint8_t(i);
        }
    }
};
NativeSimpleTable native_simple_table;
bool native_simple_ready;
NativeSimpleTable& NativeSimpleMapping() {
    if (!native_simple_ready) {
        native_simple_table.Build();
        native_simple_ready = true;
    }
    return native_simple_table;
}
// A native setter just wrote both the guest state and its effective method.
// Advance that one pair in the saved comparison, leaving independent writes
// and ambiguous (duplicate) encodings to the next full reconciliation.
void RememberSimpleWrite(unsigned state, unsigned method, uint32_t value) {
    auto& table = native_simple_table;
    if (!native_simple_ready || !table.hydrated || state >= table.next.size() ||
        method < 0x300 || method >= 0x400 || (method & 3) ||
        table.first[method / 4] != state || table.next[state] != NativeSimpleTable::end) return;
    table.last_input[state] = value;
    table.last_output[(method - 0x300) / 4] = value;
}
void NativeSimple(uint32_t method, uint32_t value) {
    native_mesh_changed |= gpu::PreparedState::SimpleMethod(method);
    g_state.simple[(method & 0x1ffc) >> 2] = value;
    if (ngb_native_mesh_enabled) {
        if (method & ~0x1ffcu) return;
        const auto& table = NativeSimpleMapping();
        for (unsigned i = table.first[method >> 2]; i != NativeSimpleTable::end; i = table.next[i]) {
            W32(kRenderState + i * 4, value);
            RememberSimpleWrite(i, method, value);
        }
    } else {
        for (uint32_t i = 0; i < gpu::kRsDeferredFirst; ++i)
            if ((R32(kSimpleEncode + i * 4) & 0x1ffc) == method) W32(kRenderState + i * 4, value);
    }
}
void NativeSyncSimple() {
    const auto* states = static_cast<const uint32_t*>(HostPtr(kRenderState));
    if (ngb_native_mesh_enabled) {
        auto& table = NativeSimpleMapping();
        const auto* output = g_state.simple.data() + 0x300 / 4;
        auto& clip = g_state.simple[0x1d78 / 4];
        // Both sides can be edited independently by inline Xbox writes or HLE setters.
        if (table.hydrated && clip == table.last_clip &&
            !std::memcmp(states, table.last_input.data(), sizeof(table.last_input)) &&
            !std::memcmp(output, table.last_output.data(), sizeof(table.last_output))) return;
        native_mesh_changed |= gpu::PreparedState::Simple | gpu::PreparedState::DepthClip;
        for (unsigned i = 0; i < table.count; ++i)
            g_state.simple[table.copies[i].method] = states[table.copies[i].state];
        std::memcpy(table.last_input.data(), states, sizeof(table.last_input));
        std::memcpy(table.last_output.data(), output, sizeof(table.last_output));
        table.last_clip = clip;
        table.hydrated = true;
    } else {
        native_mesh_changed |= gpu::PreparedState::Simple | gpu::PreparedState::DepthClip;
        const auto* methods = static_cast<const uint32_t*>(HostPtr(kSimpleEncode));
        for (uint32_t i = 0; i < gpu::kRsDeferredFirst; ++i) {
            uint32_t method = methods[i] & 0x1ffc;
            if ((method >= 0x300 && method < 0x400) || method == 0x1d78)
                g_state.simple[method >> 2] = states[i];
        }
    }
}
