// Included in the diagnostic VulkanBackend class. Reuse the frame's query pool
// and fence. Timestamps bracket an actual draw at the same pipeline stage.
static constexpr uint32_t kWavePairs = 16;
static constexpr uint32_t kWaveBase = kFrameChunks * 2;
struct WaveFrame {
    uint32_t frame{}, draws[2]{}, count{}, unavailable{};
    uint8_t kind[kWavePairs]{};
} wave_[2];

uint32_t WaveTextureKind(const State& s, VkImageView view) {
    TextureDesc tex;
    if (!view || !s.textures[0] || !Describe(s.textures[0], tex) ||
        tex.format != 0x0f || tex.width != 64 || tex.height != 64 || tex.levels != 1) return ~0u;
    auto it = textures_.find((uint64_t(tex.data) << 8) | tex.format);
    if (it == textures_.end() || it->second.img.view != view) return ~0u;
    // Content signatures of the ring strips and radial sprites seen in the
    // Chapter 1 charge capture. Their guest allocation addresses can change.
    auto sig = it->second.sig;
    if (sig == 0x2a0d54a2e9a6ff2cull) return 0;
    if (sig == 0x17089f92ab5872b7ull) return 1;
    return ~0u;
}
uint32_t WaveBegin(const State& s, VkImageView view) {
    unsigned kind = WaveTextureKind(s, view);
    if (kind == ~0u) return ~0u;
    auto& w = wave_[slot_];
    w.frame = frame_ + 1;
    ++w.draws[kind];
    if (w.frame % 4 != 0) return ~0u;
    if (!ts_pool_[slot_] || w.count == kWavePairs) { ++w.unavailable; return ~0u; }
    w.kind[w.count] = uint8_t(kind);
    uint32_t q = kWaveBase + 2 * w.count++;
    d_.vkCmdWriteTimestamp(cmd_, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, ts_pool_[slot_], q);
    return q;
}
void WaveRead(int slot) {
    auto& w = wave_[slot];
    if (!w.frame) return;
    uint32_t valid[2]{};
    uint64_t ns[2]{};
    if (w.count) {
        std::array<uint64_t, 2 * kWavePairs> t{};
        VkResult rc = d_.vkGetQueryPoolResults(dev_, ts_pool_[slot], kWaveBase, 2 * w.count,
            sizeof(t), t.data(), sizeof(uint64_t), VK_QUERY_RESULT_64_BIT);
        if (rc == VK_SUCCESS) {
            for (unsigned i = 0; i < w.count; ++i) {
                unsigned k = w.kind[i];
                ++valid[k];
                ns[k] += uint64_t(double((t[2*i+1] - t[2*i]) & ts_mask_) * ts_period_ns_);
            }
        } else w.unavailable += w.count;
    }
    uint64_t v[]{w.frame,w.draws[0],w.draws[1],valid[0],valid[1],ns[0],ns[1],w.unavailable};
    ngb_combat_row('W', v, 8);
    w = {};
}

// Alternate coarse draw groups and material groups on frames 2 and 6
// of each eight. Frames with the existing wave probes never overlap these.
enum Phase : unsigned { Opaque, Alpha, Additive, Offscreen, Composite, History, Scanout, Feedback, SurfaceCopy, PhaseCount };
static constexpr unsigned kPhaseBase = kWaveBase + 2 * kWavePairs;
static constexpr unsigned kPhasePairs = 384;
enum EffectPass : unsigned { OtherPass, HistoryMix512, AddFrom128, RingWithTarget, EffectPassCount };
struct PhaseKey {
    Phase kind;
    uint64_t sig{}, shader{}, second{};
    unsigned w{}, h{}, fmt{}, src{}, dst{}, targets{};
    EffectPass pass{};
    bool operator==(const PhaseKey& b) const {
        return kind == b.kind && sig == b.sig && w == b.w && h == b.h &&
               fmt == b.fmt && src == b.src && dst == b.dst &&
               shader == b.shader && second == b.second && targets == b.targets && pass == b.pass;
    }
};
struct PhaseSpan { PhaseKey key; unsigned calls; };
struct PhaseFrame {
    unsigned frame{}, count{}, omitted{}, calls[PhaseCount]{};
    uint64_t feedback_pixels{}, copy_pixels{};
    unsigned pass_calls[EffectPassCount]{};
    bool open{};
    PhaseSpan spans[kPhasePairs];
} phase_[2]{};
unsigned phase_reset_[2]{2 * kPhasePairs, 2 * kPhasePairs};
bool phase_probe_{};

void PhaseEnd() {
    auto& p = phase_[slot_];
    if (!p.open) return;
    d_.vkCmdWriteTimestamp(cmd_, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, ts_pool_[slot_],
                           kPhaseBase + 2 * p.count - 1);
    p.open = false;
}
void PhaseBegin(PhaseKey key) {
    auto& p = phase_[slot_];
    p.frame = frame_ + 1;
    ++p.calls[key.kind];
    ++p.pass_calls[key.pass];
    if (p.open && p.spans[p.count - 1].key == key) {
        ++p.spans[p.count - 1].calls;
        return;
    }
    PhaseEnd();
    if (!ts_pool_[slot_] || p.count == kPhasePairs) { ++p.omitted; return; }
    d_.vkCmdWriteTimestamp(cmd_, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, ts_pool_[slot_],
                           kPhaseBase + 2 * p.count);
    p.spans[p.count++] = {key, 1};
    p.open = true;
}
void PhaseDraw(Phase kind, const PipeKey& pipe, const State& s, const VkImageView* views, const bool* from_target, EffectPass pass) {
    PhaseKey key{kind};
    key.pass = pass;
    if (((frame_ + 1) & 7) == 6) {
        key.src = pipe.src;
        key.dst = pipe.dst;
        key.shader = pipe.ps;
        for (unsigned i = 0; i < 4; ++i)
            if (from_target[i]) key.targets |= 1u << i;
        for (unsigned i = 0; i < 2; ++i) {
            TextureDesc tex;
            if (!views[i] || !s.textures[i] || !Describe(s.textures[i], tex)) continue;
            if (i == 0) { key.w = tex.width; key.h = tex.height; key.fmt = tex.format; }
            if (from_target[i]) continue;
            auto it = textures_.find((uint64_t(tex.data) << 8) | tex.format);
            if (it != textures_.end() && it->second.img.view == views[i])
                (i == 0 ? key.sig : key.second) = it->second.sig;
        }
    }
    PhaseBegin(key);
}
void PhaseRead(int slot) {
    auto& p = phase_[slot];
    if (!p.frame) return;
    std::array<uint64_t, 2 * kPhasePairs> ticks;
    const bool valid = p.count && d_.vkGetQueryPoolResults(dev_, ts_pool_[slot], kPhaseBase,
        2 * p.count, sizeof(ticks), ticks.data(), sizeof(uint64_t), VK_QUERY_RESULT_64_BIT) == VK_SUCCESS;
    const bool detail = (p.frame & 7) == 6;
    uint64_t ns[PhaseCount]{}, pass_ns[EffectPassCount]{};
    struct Material { PhaseKey key; unsigned calls, spans; uint64_t ns; };
    std::array<Material, kPhasePairs> materials;
    unsigned used = 0;
    for (unsigned i = 0; valid && i < p.count; ++i) {
        const auto& span = p.spans[i];
        const auto kind = span.key.kind;
        const uint64_t cost = uint64_t(double((ticks[2*i+1] - ticks[2*i]) & ts_mask_) * ts_period_ns_);
        ns[kind] += cost;
        pass_ns[span.key.pass] += cost;
        if (!detail || kind >= Scanout) continue;
        unsigned j = 0;
        while (j < used && !(materials[j].key == span.key)) ++j;
        if (j == used) materials[used++] = {span.key, 0, 0, 0};
        materials[j].calls += span.calls;
        ++materials[j].spans;
        materials[j].ns += cost;
    }
    // Keep the original columns in place for existing capture readers.
    constexpr unsigned original = Scanout + 1;
    uint64_t a[5 + 2 * PhaseCount + 2 + 2 * (EffectPassCount - 1)]{p.frame, detail, p.count, p.omitted, valid};
    for (unsigned i = 0; i < original; ++i) {
        a[5+i] = p.calls[i];
        a[5+original+i] = ns[i];
    }
    unsigned pos = 5 + 2 * original;
    a[pos++] = p.calls[Feedback]; a[pos++] = p.calls[SurfaceCopy];
    a[pos++] = ns[Feedback]; a[pos++] = ns[SurfaceCopy];
    a[pos++] = p.feedback_pixels; a[pos++] = p.copy_pixels;
    for (unsigned pass = HistoryMix512; pass < EffectPassCount; ++pass) {
        a[pos++] = p.pass_calls[pass];
        a[pos++] = pass_ns[pass];
    }
    ngb_combat_row('A', a, pos);
    std::sort(materials.begin(), materials.begin()+used,
                      [](const Material& x, const Material& y) { return x.ns > y.ns; });
    unsigned blends = 0, seen = 0;
    for (unsigned i = 0; i < used; ++i) {
        const auto& m = materials[i]; const auto& k = m.key;
        if (k.kind == Alpha || k.kind == Additive) {
            if (++blends > 3) continue;
        } else {
            const unsigned bit = 1u << (k.pass == HistoryMix512 ? PhaseCount : k.kind);
            if (seen & bit) continue;
            seen |= bit;
        }
        uint64_t l[]{p.frame, k.kind, k.sig, k.w, k.h, k.fmt, k.src, k.dst, m.calls, m.spans, m.ns, k.shader, k.second, k.targets};
        ngb_combat_row('L', l, sizeof(l)/sizeof(*l));
    }
    // Unused queries remain reset, only the used prefix needs resetting for reuse.
    phase_reset_[slot] = 2 * p.count;
    p.frame = p.count = p.omitted = 0;
    p.feedback_pixels = p.copy_pixels = 0;
    std::fill_n(p.pass_calls, EffectPassCount, 0u);
    std::fill_n(p.calls, PhaseCount, 0u);
}
