// Native implementation of NGB's XDK 5849 graphics boundary. Guest-visible
// layouts follow the game and ngb-pc-native-port/black-pc (GPL-2.0-or-later).
// Included by hle.cpp: the Vulkan state translator and shader decoders are shared.
// No original D3D body is a fallback in this mode. Unknown entry points stop.

constexpr uint32_t kNativeDevice = 0x003D5F20;
constexpr uint32_t kNativeDeviceBytes = 0x24A8;
constexpr uint32_t kNativePushBytes = 1024 * 1024;
uint32_t native_push, native_read, native_lights, native_back, native_front, native_depth;
uint32_t native_prim, native_callback, native_last_report, native_draws, native_frames;
uint32_t native_completed_draws;
uint64_t native_vblank_due;
NativeFramePacer native_pacer;
bool native_flushing, native_polling;
std::vector<uint32_t> native_inline;
std::vector<std::array<float, 64>> native_vertices;
std::array<float, 64> native_attributes;
uint32_t native_attribute_mask;
uint32_t native_scratch, native_scratch_bytes;
uint32_t native_callback_data, native_vblanks, native_present_blank;
struct NativeCallback { uint32_t function, argument, fence, report; };
std::deque<NativeCallback> native_callbacks;
uint64_t native_calls[D3DF_COUNT]{};
std::unordered_map<uint32_t, uint64_t> native_helper_calls;
uint32_t native_current_fn;
struct NativeResourceEvent { uint32_t frame, call, action, common, data; };
std::unordered_map<uint32_t, std::deque<NativeResourceEvent>> native_resource_events;
void NativeResourceTrace(uint32_t p, uint32_t action) {
    static const bool on = std::getenv("NGB_NATIVE_RESOURCE_TRACE") != nullptr;
    if (!on || !p) return;
    auto& q = native_resource_events[p];
    if (q.size() == 24) q.pop_front();
    q.push_back({native_frames, native_current_fn, action, R32(p), R32(p + 4)});
}

extern "C" uint32_t ngb_contiguous_allocate(uint32_t, uint32_t, uint32_t, uint32_t, uint32_t);
extern "C" int ngb_contiguous_free(uint32_t);
extern "C" void ngb_pad_flip(void);
extern "C" void ngb_scanout_mode(uint32_t, uint32_t, uint32_t, uint32_t);

uint32_t NativePool(uint32_t bytes) {
    uint32_t p = ngb_graphics_pool_alloc(bytes);
    if (!p) ngb_stop("native graphics pool exhausted", bytes);
    std::memset(HostPtr(p, bytes), 0, bytes);
    return p;
}

uint32_t NativeData(uint32_t bytes) {
    uint32_t p = ngb_contiguous_allocate(std::max(bytes, 1u), 0, UINT32_MAX, 4096, 4);
    if (!p) ngb_stop("native graphics data exhausted", bytes);
    std::memset(HostPtr(p, std::max(bytes, 1u)), 0, std::max(bytes, 1u));
    return p & 0x0fffffffu;
}

uint32_t NativeHeader(uint32_t bytes) {
    // Game-inline DeleteShader/Release can hand this allocation to RtlFreeHeap.
    // Use the title's heap allocator (outside D3D), not one VM page per header.
    uint32_t args[] = {0x40, bytes};
    uint32_t p = ngb_graphics_guest_call(0x0032cffd, args, 2);
    if (!p) ngb_stop("native graphics header allocation failed", bytes);
    std::memset(HostPtr(p, bytes), 0, bytes); return p;
}

uint32_t NativeSurface(uint32_t width, uint32_t height, uint32_t format) {
    const auto& f = gpu::Format(format);
    if (!f.bits || f.swizzled || f.compressed || !width || !height)
        ngb_stop("invalid native frame buffer format", format);
    uint32_t pitch = ((width * f.bits / 8) + 63) & ~63u;
    uint32_t p = NativeHeader(24);
    W32(p, 0x81050001); W32(p + 4, NativeData(pitch * height));
    W32(p + 12, 0x10021 | (format << 8));
    W32(p + 16, (width - 1) | ((height - 1) << 12) | ((pitch / 64 - 1) << 24));
    return p;
}

uint32_t NativeTextureHeader(uint32_t width, uint32_t height, uint32_t depth, uint32_t levels,
                             uint32_t format, uint32_t pitch, bool cube, bool volume,
                             uint32_t out_format, uint32_t out_size) {
    const auto& f = gpu::Format(format);
    if (!width || !height || !f.bits) ngb_stop("invalid native texture dimensions/format", format);
    auto log2 = [](uint32_t v) { uint32_t n = 0; while (n < 15 && (1u << n) < v) ++n; return n; };
    gpu::TextureDesc d;
    d.width = width; d.height = height; d.depth = std::max(depth, 1u); d.format = format;
    d.linear = !f.swizzled && !f.compressed; d.cube = cube;
    uint32_t fmt, size = 0;
    if (d.linear) {
        d.pitch = pitch ? pitch : ((width * f.bits / 8 + 63) & ~63u);
        fmt = 0x10029 | (format << 8);
        size = (width - 1) | ((height - 1) << 12) | ((d.pitch / 64 - 1) << 24);
    } else {
        uint32_t max_levels = log2(std::max({width, height, volume ? d.depth : 1u})) + 1;
        d.levels = levels ? std::min(levels, max_levels) : max_levels;
        fmt = 9 | (cube ? 4 : 0) | ((volume ? 3u : 2u) << 4) | (format << 8) |
              (d.levels << 16) | (log2(width) << 20) | (log2(height) << 24) | (log2(d.depth) << 28);
    }
    W32(out_format, fmt); W32(out_size, size);
    return gpu::TotalSize(d);
}

uint32_t NativeCreateSurface(uint32_t width, uint32_t height, uint32_t format) {
    uint32_t p = NativeHeader(24);
    uint32_t bytes = NativeTextureHeader(width, height, 1, 1, format, 0, false, false, p + 12, p + 16);
    W32(p, 0x81050001); W32(p + 4, NativeData(bytes)); return p;
}

void NativeSurfaceDesc(uint32_t header, uint32_t level, uint32_t out) {
    gpu::TextureDesc d;
    if (!gpu::Describe(header, d) || level >= d.levels) ngb_stop("invalid native surface description", header);
    uint32_t desc[] = {d.format, 1, 0, gpu::LevelSize(d, level), 0x11,
                       std::max(d.width >> level, 1u), std::max(d.height >> level, 1u)};
    std::memcpy(HostPtr(out, sizeof desc), desc, sizeof desc);
}

void NativeDestroy(uint32_t resource);
uint32_t NativeAddRef(uint32_t resource) {
    if (!resource) return 0;
    uint32_t common = R32(resource);
    if (!(common & 0xffff) && (common & 0x70000) == 0x50000 && R32(resource + 20))
        NativeAddRef(R32(resource + 20));
    W32(resource, common + 1); return (common + 1) & 0xffff;
}
uint32_t NativeRelease(uint32_t resource) {
    if (!resource) return 0;
    NativeResourceTrace(resource, 3);
    uint32_t common = R32(resource), refs = common & 0xffff;
    if (!refs) return 0;
    W32(resource, common - 1);
    if (refs == 1 && (common & 0x70000) == 0x50000 && R32(resource + 20))
        NativeRelease(R32(resource + 20));
    if (refs == 1 && !(R32(resource) & 0x780000)) NativeDestroy(resource);
    return refs - 1;
}

void NativeDestroy(uint32_t resource) {
    native_mesh_coherent = false;
    if (!resource || (R32(resource) & 0x780000)) return;
    uint32_t common = R32(resource);
    uint32_t type = common & 0x70000;
    uint32_t parent = type == 0x50000 ? R32(resource + 20) : 0;
    if (parent) {
        // A surface view owns only its header. Recorded commands already keep
        // their own header copy. Release/Unbind drops the parent's reference
        // first, and the parent waits if that really destroys the shared data.
        // Neither wait for nor invalidate live texture data when a view dies.
        if (common & 0x01000000) ngb_graphics_guest_call(0x0032d01a, &resource, 1);
        return;
    }
    if (g_backend) g_backend->WaitResource(resource);
    gpu::MarkDirty(resource);
    if (!(common & 0x01000000)) return; // game-owned headers and storage
    uint32_t data = R32(resource + 4);
    // Index/fixup headers describe borrowed storage; surface/push-buffer
    // ownership is in bit 31, with opposite polarity for those two types.
    bool owns_data = type != 0x10000 && type != 0x60000 &&
                     (type != 0x50000 || (common & 0x80000000u)) &&
                     (type != 0x20000 || !(common & 0x80000000u));
    if (owns_data && data && !ngb_contiguous_free(data | 0x80000000u)) {
        std::fprintf(stderr, "[NATIVE-XDK] release header=%08x common=%08x data=%08x parent=%08x\n",
                     resource, common, data, parent);
        for (const auto& e : native_resource_events[resource])
            std::fprintf(stderr,"[RESOURCE] f=%u call=%x action=%u common=%08x data=%08x\n",e.frame,e.call,e.action,e.common,e.data);
        ngb_stop("native resource data release failed", data);
    }
    ngb_graphics_guest_call(0x0032d01a, &resource, 1);
}

void NativeBind(uint32_t old_resource, uint32_t resource) {
    if (resource == old_resource) return;
    if (resource) {
        NativeResourceTrace(resource, 1);
        uint32_t common = R32(resource);
        if (!(common & 0x780000) && (common & 0x70000) == 0x50000 && R32(resource + 20))
            NativeBind(0, R32(resource + 20));
        W32(resource, R32(resource) + 0x80000);
    }
    if (old_resource) {
        NativeResourceTrace(old_resource, 2);
        if (!(R32(old_resource) & 0x780000)) ngb_stop("native binding imbalance", old_resource);
        uint32_t common = R32(old_resource);
        if ((common & 0x780000) == 0x80000 && (common & 0x70000) == 0x50000 && R32(old_resource + 20))
            NativeBind(R32(old_resource + 20), 0);
        W32(old_resource + 8, R32(kNativeDevice + 0x2c));
        W32(old_resource, R32(old_resource) - 0x80000);
        if (!(R32(old_resource) & 0x78ffff)) NativeDestroy(old_resource);
    }
}

void NativeViewportConstants(std::array<float, 4>& scale, std::array<float, 4>& offset) {
    ViewportConstants(scale, offset);
    float x, y;
    std::memcpy(&x, HostPtr(kNativeDevice + 0xef8, 4), 4);
    std::memcpy(&y, HostPtr(kNativeDevice + 0xefc, 4), 4);
    offset[0] += x - g_state.ss_offset_x;
    offset[1] += y - g_state.ss_offset_y;
    scale[3] = 1;
}

void NativeViewport() {
    uint32_t dev = R32(kDevicePtr);
    if (!dev) return;
    std::memcpy(HostPtr(dev + 0xee0, 24), &g_state.viewport, 24);
    std::array<float, 4> scale, offset;
    NativeViewportConstants(scale, offset);
    std::memcpy(HostPtr(kVsConstants + 58 * 16, 16), scale.data(), 16);
    std::memcpy(HostPtr(kVsConstants + 59 * 16, 16), offset.data(), 16);
}

void NativeDefaults() {
    std::memset(HostPtr(kRenderState, 166 * 4), 0, 166 * 4);
    std::memset(HostPtr(kTextureState, 4 * 128), 0, 4 * 128);
    for (auto v : {std::pair{gpu::kMZFunc, 0x203u}, {gpu::kMAlphaFunc, 0x207u},
                   {gpu::kMSrcBlend, 1u}, {gpu::kMDestBlend, 0u}, {gpu::kMZWriteEnable, 1u},
                   {gpu::kMShadeMode, 0x1d01u}, {gpu::kMColorWriteEnable, 0x01010101u},
                   {gpu::kMStencilZFail, 0x1e00u}, {gpu::kMStencilPass, 0x1e00u},
                   {gpu::kMStencilFunc, 0x207u}, {gpu::kMStencilMask, ~0u},
                   {gpu::kMStencilWriteMask, ~0u}, {gpu::kMBlendOp, 0x8006u}}) NativeSimple(v.first, v.second);
    auto state = [](uint32_t i, uint32_t v) { W32(kRenderState + i * 4, v); g_state.rs[i] = v; };
    for (uint32_t i : {gpu::kRsFogEnd, gpu::kRsFogDensity, gpu::kRsPointSize, gpu::kRsPointScaleA}) state(i, 0x3f800000);
    for (uint32_t i : {gpu::kRsLighting, gpu::kRsLocalViewer, gpu::kRsColorVertex, gpu::kRsDiffuseMaterialSource,
                       gpu::kRsZEnable}) state(i, 1);
    state(gpu::kRsSpecularMaterialSource, 2); state(gpu::kRsPointSizeMax, 0x42800000);
    state(gpu::kRsFillMode, 0x1b02); state(gpu::kRsBackFillMode, 0x1b02);
    state(gpu::kRsFrontFace, 0x900); state(gpu::kRsCullMode, 0x901);
    state(gpu::kRsTextureFactor, ~0u); state(gpu::kRsMultiSampleMask, ~0u); state(gpu::kRsStencilFail, 0x1e00);
    for (uint32_t s = 0; s < 4; ++s) {
        auto ts = [&](uint32_t i, uint32_t v) { W32(kTextureState + s * 128 + i * 4, v); g_state.tss[s][i] = v; };
        for (uint32_t i : {0u, 1u, 2u, 8u, 15u, 19u, 20u}) ts(i, 1);
        for (uint32_t i : {3u, 4u, 14u, 18u}) ts(i, 2);
        ts(12, s ? 1 : 4); ts(16, s ? 1 : 2); ts(28, s);
    }
}

void NativeCreate(uint32_t params, uint32_t out) {
    native_simple_ready = false;
    if (native_push) ngb_stop("duplicate native device creation", params);
    uint32_t width = R32(params), height = R32(params + 4);
    if (!width) width = 640;
    if (!height) height = 480;
    std::memset(HostPtr(kNativeDevice, kNativeDeviceBytes), 0, kNativeDeviceBytes);
    std::memset(HostPtr(0x3d93a8, 16 * 12), 0, 16 * 12);
    W32(kDevicePtr, kNativeDevice);
    native_push = NativePool(kNativePushBytes); native_read = native_push;
    W32(kNativeDevice, native_push); W32(kNativeDevice + 4, native_push + kNativePushBytes - 65536);
    W32(0x3d9588, 0x2000);
    W32(kNativeDevice + 0x96c, 0x3f800000); W32(kNativeDevice + 0x970, 0x3f800000);
    W32(kNativeDevice + 0xef8, 0x3f080000); W32(kNativeDevice + 0xefc, 0x3f080000);
    // The shared Vulkan translator takes the API's offset; the guest device
    // stores the XDK's additional half-pixel/sample-grid bias.
    g_state.ss_offset_x = g_state.ss_offset_y = 0;
    uint32_t cf = gpu::LinearColorFormat(R32(params + 8));
    uint32_t zf = gpu::LinearDepthFormat(R32(params + 36));
    native_back = NativeSurface(width, height, cf);
    native_front = NativeSurface(width, height, cf);
    native_depth = R32(params + 32) ? NativeSurface(width, height, zf) : 0;
    W32(kNativeDevice + 0x1a04, native_back); W32(kNativeDevice + 0x1a08, native_depth);
    W32(kNativeDevice + 0x1a14, native_back); W32(kNativeDevice + 0x1a18, native_front);
    NativeBind(0, native_back); NativeBind(0, native_depth);
    g_state.rt = SurfaceOf(native_back); g_state.zs = SurfaceOf(native_depth);
    g_state.viewport = {0, 0, width, height, 0, 1};
    for (uint32_t t = 0; t < 10; ++t) {
        uint32_t pc = t < 2 ? t + 2 : t < 6 ? t + 14 : t + 250;
        for (uint32_t i = 0; i < 16; ++i) {
            uint32_t v = i % 5 == 0 ? 0x3f800000 : 0;
            W32(kNativeDevice + 0xc60 + t * 64 + i * 4, v); g_state.transforms[pc][i] = v;
        }
    }
    native_lights = NativePool(256 * 0x90);
    native_callback_data = NativePool(20);
    W32(kNativeDevice + 0x1dbc, 0x00040001); // synchronization event
    W32(kNativeDevice + 0x1dc4, kNativeDevice + 0x1dc4);
    W32(kNativeDevice + 0x1dc8, kNativeDevice + 0x1dc4);
    for (unsigned i = 0; i < 256; ++i) W32(native_lights + i * 0x90 + 0x8c, ~0u);
    W32(kNativeDevice + 0x7a4, native_lights); W32(kNativeDevice + 0x7a8, 256);
    NativeDefaults(); NativeViewport();
    W32(kRenderState + gpu::kRsPresentationInterval * 4, R32(params + 48));
    if (out) W32(out, kNativeDevice);
    ngb_scene_native_start();
    Start();
    ngb_scanout_mode(0x0802020e, 0x12, ((width * 4 + 63) & ~63u), R32(native_back + 4));
    native_vblank_due = ngb_elapsed_ns() + 16666667;
    native_pacer = {};
    std::fprintf(stderr, "[NATIVE-XDK] created %ux%u, original D3D bodies disabled\n", width, height);
}

void NativeFlush();

uint32_t NativeLight(uint32_t index) {
    uint32_t count = R32(kNativeDevice + 0x7a8);
    if (index >= count) {
        if (index >= 65536) ngb_stop("native light storage exhausted", index);
        uint32_t next = std::max(256u, count);
        while (next <= index) next *= 2;
        uint32_t replacement = NativePool(next * 0x90);
        std::memcpy(HostPtr(replacement, count * 0x90), HostPtr(native_lights, count * 0x90), count * 0x90);
        for (uint32_t i = count; i < next; ++i) W32(replacement + i * 0x90 + 0x8c, ~0u);
        for (unsigned i = 0; i < 8; ++i) {
            uint32_t slot = kNativeDevice + 0x7ac + i * 4, old = R32(slot);
            if (old) W32(slot, replacement + old - native_lights);
        }
        ngb_graphics_pool_free(native_lights); native_lights = replacement;
        W32(kNativeDevice + 0x7a4, native_lights); W32(kNativeDevice + 0x7a8, next);
    }
    return native_lights + index * 0x90;
}

void NativeSetLight(uint32_t index, uint32_t source) {
    uint32_t light = NativeLight(index);
    std::memcpy(HostPtr(light, 104), HostPtr(source, 104), 104);
    W32(light + 0x68, R32(light + 0x68) | 3);
    for (unsigned i = 0; i < 3; ++i) {
        float value; std::memcpy(&value, HostPtr(source + 64 + i * 4, 4), 4); value = -value;
        std::memcpy(HostPtr(light + 0x6c + i * 4, 4), &value, 4);
    }
    uint32_t slot = R32(light + 0x8c);
    if (slot < 8) {
        std::memcpy(g_state.lights[slot].data(), HostPtr(light, 104), 104);
        ++g_state.lights_revision;
    }
}

void NativeLightEnable(uint32_t index, bool enabled) {
    uint32_t light = NativeLight(index), slot = R32(light + 0x8c);
    if (!R32(light)) {
        W32(light, 3); for (unsigned i = 1; i <= 3; ++i) W32(light + i * 4, 0x3f800000);
        W32(light + 72, 0x3f800000); W32(light + 0x6c + 8, 0xbf800000);
    }
    uint32_t control = R32(kNativeDevice + 0x7cc);
    if (enabled && slot == ~0u) {
        for (slot = 0; slot < 8 && ((control >> (slot * 2)) & 3); ++slot) {}
        if (slot == 8) ngb_stop("native light slots exhausted", index);
        uint32_t type = R32(light);
        control |= (type == 3 ? 1 : type + 1) << (slot * 2);
        W32(light + 0x8c, slot); W32(kNativeDevice + 0x7ac + slot * 4, light);
        g_state.light_enable |= 1u << slot;
        std::memcpy(g_state.lights[slot].data(), HostPtr(light, 104), 104);
    } else if (!enabled && slot < 8) {
        control &= ~(3u << (slot * 2)); W32(kNativeDevice + 0x7ac + slot * 4, 0);
        W32(light + 0x8c, ~0u); g_state.light_enable &= ~(1u << slot);
    }
    W32(light + 0x68, R32(light + 0x68) | 4);
    W32(kNativeDevice + 0x7cc, control); ++g_state.lights_revision;
}

void NativeReset(uint32_t params) {
    if (g_backend) g_backend->WaitFence(g_backend->Fence());
    uint32_t width = R32(params), height = R32(params + 4);
    if (!width || !height) ngb_stop("invalid native reset size", params);
    uint32_t old_back = native_back, old_front = native_front, old_depth = native_depth;
    native_back = NativeSurface(width, height, gpu::LinearColorFormat(R32(params + 8)));
    native_front = NativeSurface(width, height, gpu::LinearColorFormat(R32(params + 8)));
    native_depth = R32(params + 32) ? NativeSurface(width, height, gpu::LinearDepthFormat(R32(params + 36))) : 0;
    NativeBind(g_state.rt.header, native_back); NativeBind(g_state.zs.header, native_depth);
    g_state.rt = SurfaceOf(native_back); g_state.zs = SurfaceOf(native_depth);
    W32(kNativeDevice + 0x1a04, native_back); W32(kNativeDevice + 0x1a08, native_depth);
    W32(kNativeDevice + 0x1a14, native_back); W32(kNativeDevice + 0x1a18, native_front);
    NativeRelease(old_back); NativeRelease(old_front); NativeRelease(old_depth);
    g_state.viewport = {0, 0, width, height, 0, 1}; g_state.scissor_count = 0;
    NativeViewport();
}

void NativeDestroyDevice() {
    if (!native_push) return;
    if (g_backend) { g_backend->Flush(); g_backend->WaitFence(g_backend->Fence()); }
    for (unsigned i = 0; i < 4; ++i) {
        NativeBind(R32(kNativeDevice + 0xf88 + i * 4), 0);
        NativeBind(R32(kNativeDevice + 0xf98 + i * 4), 0);
    }
    for (unsigned i = 0; i < 16; ++i) NativeBind(R32(0x3d93b0 + i * 12), 0);
    NativeBind(g_state.rt.header, 0); NativeBind(g_state.zs.header, 0);
    NativeRelease(native_back); NativeRelease(native_front); NativeRelease(native_depth);
    for (unsigned i = 0; i < 64; ++i) {
        uint32_t p = R32(kNativeDevice + 0x7d4 + i * 4);
        if (p) ngb_graphics_pool_free(p);
    }
    for (uint32_t p : {native_lights, native_callback_data, native_push, native_scratch})
        if (p) ngb_graphics_pool_free(p);
    native_push = native_read = native_lights = native_back = native_front = native_depth = 0;
    native_scratch = native_scratch_bytes = native_callback_data = native_vblanks = 0;
    native_callbacks.clear(); native_inline.clear(); native_vertices.clear();
    native_prim = native_callback = native_last_report = 0;
    native_pacer = {};
    g_backend.reset(); g_started = false; g_state = gpu::State{};
    g_vs.clear(); g_ps.clear(); g_selected.reset();
    W32(kDevicePtr, 0);
}
void NativeImmediateEnd() {
    if (!native_prim) return;
    auto upload = [](const void* data, uint32_t bytes, uint32_t stride, uint32_t count) {
        if (bytes > native_scratch_bytes) {
            if (native_scratch) ngb_graphics_pool_free(native_scratch);
            native_scratch_bytes = (bytes + 65535) & ~65535u;
            native_scratch = NativePool(native_scratch_bytes);
        }
        std::memcpy(HostPtr(native_scratch, bytes), data, bytes);
        auto saved = g_state.streams[0];
        if (!guest_header) guest_header = NativePool(20);
        W32(guest_header, 0x80000001); W32(guest_header + 4, native_scratch);
        g_state.streams[0] = {guest_header, stride};
        // Recorded::Draw copies UP vertices before returning; scratch can be reused.
        Draw(native_prim, 0, count, nullptr);
        g_state.streams[0] = saved;
    };
    if (!native_inline.empty()) {
        gpu::VertexShader fvf;
        const gpu::VertexShader* layout = g_state.vs.get();
        if (!(g_state.vs_handle & 1)) { gpu::FvfInputs(g_state.vs_handle, fvf); layout = &fvf; }
        uint32_t stride = layout ? layout->stream_stride[0] : 0;
        if (!stride || (native_inline.size() * 4) % stride) ngb_stop("invalid inline vertex stride", stride);
        upload(native_inline.data(), uint32_t(native_inline.size() * 4), stride, uint32_t(native_inline.size() * 4 / stride));
    }
    if (!native_vertices.empty()) {
        if (g_state.vs_handle & 1) {
            auto saved = g_state.vs;
            auto layout = saved ? std::make_shared<gpu::VertexShader>(*saved) : std::make_shared<gpu::VertexShader>();
            for (unsigned i = 0; i < 16; ++i) layout->inputs[i] = {0, i * 16, 0x42};
            layout->stream_stride.fill(0); layout->stream_stride[0] = 256;
            g_state.vs = layout;
            upload(native_vertices.data(), uint32_t(native_vertices.size() * 256), 256, uint32_t(native_vertices.size()));
            g_state.vs = saved;
        } else {
            // Keep the FVF, including XYZRHW, and pack attributes into its layout.
            gpu::VertexShader layout; gpu::FvfInputs(g_state.vs_handle, layout);
            uint32_t stride = layout.stream_stride[0];
            if (!stride) ngb_stop("invalid immediate FVF", g_state.vs_handle);
            std::vector<uint8_t> packed(native_vertices.size() * stride);
            for (size_t v = 0; v < native_vertices.size(); ++v) for (unsigned r = 0; r < 16; ++r) {
                const auto& in = layout.inputs[r];
                if (in.stream < 0) continue;
                auto* dst = packed.data() + v * stride + in.offset;
                const auto* src = native_vertices[v].data() + r * 4;
                if (in.type == 0x40) {
                    std::array<float, 4> color; std::copy_n(src, 4, color.begin());
                    uint32_t value = gpu::PackColor(color); std::memcpy(dst, &value, 4);
                } else std::memcpy(dst, src, (in.type >> 4) * 4);
            }
            upload(packed.data(), uint32_t(packed.size()), stride, uint32_t(native_vertices.size()));
        }
    }
    native_prim = 0; native_inline.clear(); native_vertices.clear();
}

void NativeMethod(uint32_t method, uint32_t value) {
    auto attribute = [](unsigned r, float x, float y, float z, float w) {
        native_attributes[r * 4] = x; native_attributes[r * 4 + 1] = y;
        native_attributes[r * 4 + 2] = z; native_attributes[r * 4 + 3] = w;
        native_attribute_mask |= 1u << r;
        if (!r && native_prim) native_vertices.push_back(native_attributes);
    };
    if (method >= 0x1880 && method < 0x1900) {
        unsigned r = (method - 0x1880) / 8, c = (method & 4) / 4;
        std::memcpy(&native_attributes[r * 4 + c], &value, 4);
        if (c) attribute(r, native_attributes[r * 4], native_attributes[r * 4 + 1], 0, 1);
        return;
    }
    if (method >= 0x1900 && method < 0x1940) {
        attribute((method - 0x1900) / 4, int16_t(value), int16_t(value >> 16), 0, 1); return;
    }
    if (method >= 0x1940 && method < 0x1980) {
        attribute((method - 0x1940) / 4, (value & 255) / 255.f, ((value >> 8) & 255) / 255.f,
                  ((value >> 16) & 255) / 255.f, (value >> 24) / 255.f); return;
    }
    if (method >= 0x1980 && method < 0x1a00) {
        unsigned r = (method - 0x1980) / 8, c = (method & 4) / 2;
        native_attributes[r * 4 + c] = int16_t(value); native_attributes[r * 4 + c + 1] = int16_t(value >> 16);
        if (c) attribute(r, native_attributes[r * 4], native_attributes[r * 4 + 1], native_attributes[r * 4 + 2], native_attributes[r * 4 + 3]);
        return;
    }
    if (method >= 0x1a00 && method < 0x1b00) {
        unsigned i = (method - 0x1a00) / 4; std::memcpy(&native_attributes[i], &value, 4);
        native_attribute_mask |= 1u << (i / 4);
        if (i == 3 && native_prim) native_vertices.push_back(native_attributes);
        return;
    }
    switch (method) {
    case 0x100: case 0x110: case 0x1710: case 0x17c8: return;
    case 0x17cc: if (value && g_backend) g_backend->VisibilityBegin(); return;
    case 0x17fc:
        if (!value) NativeImmediateEnd();
        else { if (native_prim) ngb_stop("nested immediate primitive", value); native_prim = value; native_attribute_mask = 0; }
        return;
    case 0x1818: native_inline.push_back(value); return;
    case 0x1d8c: native_callback = value; return;
    case 0x1d90:
        if (native_callback) native_callbacks.push_back({native_callback, value,
            g_backend ? g_backend->Fence() : 0, native_last_report});
        native_last_report = 0;
        return;
    default:
        if ((method >= 0x300 && method < 0x400) || method == 0x1d78) { NativeSimple(method, value); return; }
        ngb_stop("unhandled native inline GPU method", method);
    }
}

void NativeFlush() {
    if (!native_push || native_flushing) return;
    uint32_t put = R32(kNativeDevice);
    if (put == native_read) return;
    native_mesh_coherent = false;
    NativeDiagScope diag(ND_INLINE);
    native_flushing = true;
    if (put < native_read || put > native_push + kNativePushBytes || (put & 3))
        ngb_stop("invalid native inline buffer cursor", put);
    NativeDiagWords((put - native_read) / 4);
    while (native_read < put) {
        uint32_t word = R32(native_read); native_read += 4;
        if (!word) continue;
        uint32_t count = (word >> 18) & 0x7ff, method = word & 0x1ffc;
        if ((word & 3) || ((word >> 13) & 7) || (word & 0x20000000) || count > (put - native_read) / 4)
            ngb_stop("invalid native inline command", word);
        for (uint32_t i = 0; i < count; ++i) {
            uint32_t value = R32(native_read); native_read += 4;
            NativeMethod(method + ((word & 0x40000000) ? 0 : i * 4), value);
        }
    }
    native_flushing = false;
}

void NativePoll() {
    if (!native_push || native_polling) return;
    NativeDiagScope diag(ND_POLL);
    native_polling = true;
    uint64_t now = ngb_elapsed_ns();
    if (now >= native_vblank_due) {
        native_vblanks += uint32_t((now - native_vblank_due) / 16666667 + 1);
        native_vblank_due += ((now - native_vblank_due) / 16666667 + 1) * 16666667;
        W32(kNativeDevice + 0x1dbc + 4, 1);
        uint32_t cb = R32(kNativeDevice + 0x1db8);
        if (cb) {
            W32(native_callback_data, native_vblanks); W32(native_callback_data + 4, native_frames);
            W32(native_callback_data + 8, 0);
            NativeDiagScope callback_diag(ND_CALLBACK);
            ngb_graphics_callback(cb, native_callback_data);
        }
    }
    while (!native_callbacks.empty()) {
        auto cb = native_callbacks.front();
        if (g_backend && g_backend->FencePending(cb.fence)) break;
        if (cb.report && !__atomic_load_n(static_cast<uint64_t*>(HostPtr(cb.report, 8)), __ATOMIC_ACQUIRE)) break;
        native_callbacks.pop_front();
        NativeDiagScope callback_diag(ND_CALLBACK);
        ngb_graphics_callback(cb.function, cb.argument);
    }
    native_polling = false;
}

bool NativeCall(int fn, Call c) {
    unsigned diag_kind = ND_OTHER;
    if (fn <= D3DF_D3DDevice_SetTextureStageStateNotInline ||
        (fn >= D3DF_D3DDevice_SetTransform && fn <= D3DF_D3DDevice_SetPalette) ||
        fn == D3DF_D3DDevice_SetStreamSource || fn == D3DF_D3DDevice_SetRenderTarget ||
        fn == D3DF_D3DDevice_SetScissors || fn == D3DF_D3DDevice_SetScreenSpaceOffset) diag_kind = ND_STATE;
    else if (fn >= D3DF_D3DDevice_LoadVertexShader && fn <= D3DF_D3DDevice_SetPixelShaderConstant) diag_kind = ND_SHADER;
    else if (fn == D3DF_D3DDevice_CreateVertexBuffer2 ||
             (fn >= D3DF_D3D_DestroyResource && fn <= D3DF_D3DResource_GetType)) diag_kind = ND_RESOURCE;
    else if ((fn >= D3DF_D3DDevice_DrawVerticesUP && fn <= D3DF_D3DDevice_End) ||
             fn == D3DF_D3DDevice_RunPushBuffer) diag_kind = ND_DRAW;
    NativeDiagScope diag(diag_kind);
    struct Scope { uint32_t saved = native_current_fn; ~Scope() { native_current_fn = saved; } } scope;
    native_current_fn = d3d_funcs[fn].va;
    ++native_calls[fn];
    uint32_t ret = 0, result = 0;
    bool returns = false, translate = true;
    if (fn != D3DF_Direct3D_CreateDevice) NativeFlush();
    static constexpr uint32_t complex[] = {
        151,156,138,147,146,142,143,144,145,148,157,159,160,161,162,163,164,165,149,154,155,152,153,158,
        150,139,140,141,137,136};
    if (fn <= D3DF_D3DDevice_SetRenderState_PSTextureModes) {
        uint32_t v = c.a(0); W32(kRenderState + complex[fn] * 4, v); ret = 4;
        if (fn == D3DF_D3DDevice_SetRenderState_ZBias) {
            float bias = -float(v), slope = bias * .25f; uint32_t b, s;
            std::memcpy(&b, &bias, 4); std::memcpy(&s, &slope, 4);
            NativeSimple(0x330, v != 0); NativeSimple(0x334, v != 0); NativeSimple(0x338, v != 0);
            NativeSimple(0x384, s); NativeSimple(0x388, b);
        }
    } else switch (fn) {
    case D3DF_Direct3D_CreateDevice:
        NativeCreate(c.a(0), c.r[ECX]); ret = 4; returns = true; translate = false; break;
    case D3DF_D3DDevice_Reset:
        NativeReset(c.r[EBX]); returns = true; translate = false; break;
    case D3DF_D3DDevice_SetRenderState_Simple: NativeSimple(c.r[ECX] & 0x1ffc, c.r[EDX]); break;
    case D3DF_D3DDevice_SetTextureStageStateNotInline:
        if (c.r[EAX] >= 4 || c.r[EDX] >= 32) ngb_stop("invalid native texture state", c.r[EDX]);
        W32(kTextureState + c.r[EAX] * 128 + c.r[EDX] * 4, c.r[ECX]); break;
    case D3DF_D3DDevice_SetTextureState_TexCoordIndex:
        W32(kTextureState + (c.r[ESI] & 3) * 128 + 28 * 4, c.a(0)); ret = 4; break;
    case D3DF_D3DDevice_SetTextureState_BumpEnv:
        W32(kTextureState + (c.r[EAX] & 3) * 128 + c.a(0) * 4, c.a(1)); ret = 8; break;
    case D3DF_D3DDevice_SetTextureState_BorderColor: case D3DF_D3DDevice_SetTextureState_ColorKeyColor:
        W32(kTextureState + (c.r[EAX] & 3) * 128 + (fn == D3DF_D3DDevice_SetTextureState_BorderColor ? 29 : 30) * 4, c.r[EBX]); break;
    case D3DF_D3DDevice_SetTexture:
        NativeBind(R32(kNativeDevice + 0xf88 + (c.r[EAX] & 3) * 4), c.a(0));
        W32(kNativeDevice + 0xf88 + (c.r[EAX] & 3) * 4, c.a(0)); ret = 4; break;
    case D3DF_D3DDevice_SetPalette:
        NativeBind(R32(kNativeDevice + 0xf98 + (c.r[EAX] & 3) * 4), c.a(0));
        W32(kNativeDevice + 0xf98 + (c.r[EAX] & 3) * 4, c.a(0)); ret = 4; break;
    case D3DF_D3DDevice_SetStreamSource:
        NativeBind(R32(0x3d93b0 + (c.r[EAX] & 15) * 12), c.r[EBX]);
        W32(0x3d93b0 + (c.r[EAX] & 15) * 12, c.r[EBX]);
        W32(0x3d93a8 + (c.r[EAX] & 15) * 12, c.a(0)); ret = 4; break;
    case D3DF_D3DDevice_SetTransform:
        if (c.r[EAX] >= 10) ngb_stop("invalid native transform", c.r[EAX]);
        std::memcpy(HostPtr(kNativeDevice + 0xc60 + c.r[EAX] * 64, 64), HostPtr(c.r[EDX], 64), 64); break;
    case D3DF_D3DDevice_SetRenderTarget:
        if (c.a(0)) { NativeBind(g_state.rt.header, c.a(0)); W32(kNativeDevice + 0x1a04, c.a(0)); }
        NativeBind(g_state.zs.header, c.a(1)); W32(kNativeDevice + 0x1a08, c.a(1)); ret = 8; returns = true; break;
    case D3DF_D3DDevice_SetViewport: ret = 4; break;
    case D3DF_D3DDevice_SetLight:
        NativeSetLight(c.a(0), c.a(1)); ret = 8; returns = true; translate = false; break;
    case D3DF_D3DDevice_LightEnable:
        NativeLightEnable(c.r[EAX], c.a(0) != 0); ret = 4; returns = true; translate = false; break;
    case D3DF_D3DDevice_SetScissors: ret = 12; break;
    case D3DF_D3DDevice_SetScreenSpaceOffset:
        for (unsigned i = 0; i < 2; ++i) {
            float value = c.af(i) + .53125f;
            std::memcpy(HostPtr(kNativeDevice + 0xef8 + i * 4, 4), &value, 4);
        }
        ret = 8; break;
    case D3DF_D3DDevice_GetViewportOffsetAndScale: {
        std::array<float,4> s,o; NativeViewportConstants(s,o);
        std::memcpy(HostPtr(c.r[EDX], 16), o.data(), 16); std::memcpy(HostPtr(c.r[ECX], 16), s.data(), 16); break;
    }
    case D3DF_D3D_UpdateProjectionViewportTransform: NativeViewport(); break;
    case D3DF_D3DDevice_CreateVertexShader: {
        uint32_t h = NativeHeader(0x140) | 1;
        auto vs = ReadVertexShader(c.a(0), c.a(1)); vs->handle = h; g_vs[h] = vs;
        W32(h & ~1u, 1); W32((h & ~1u) + 4, 1); W32(c.a(2), h);
        ret = 16; returns = true; translate = false; break;
    }
    case D3DF_D3DDevice_CreatePixelShader: {
        uint32_t h = NativeHeader(0xfc); W32(h, 1); W32(h + 4, 1); W32(h + 8, h + 12);
        std::memcpy(HostPtr(h + 12, 0xf0), HostPtr(c.a(0), 0xf0), 0xf0); W32(c.a(1), h);
        ret = 8; returns = true; translate = false; break;
    }
    case D3DF_D3DDevice_SetVertexShader: W32(kNativeDevice + 0x794, c.a(0)); ret = 4; break;
    case D3DF_D3DDevice_LoadVertexShader: ret = 4; break;
    case D3DF_D3DDevice_SelectVertexShader: W32(kNativeDevice + 0x794, c.r[EAX]); break;
    case D3DF_D3DDevice_SetPixelShader:
        W32(kNativeDevice + 0x784, c.r[EAX]);
        if (c.r[EAX]) { std::memcpy(HostPtr(kRenderState, 57 * 4), HostPtr(c.r[EAX] + 12, 57 * 4), 57 * 4);
            W32(kRenderState + 136 * 4, R32(c.r[EAX] + 12 + 54 * 4));
            W32(kNativeDevice + 0x788, R32(c.r[EAX] + 12 + 0x20) | R32(c.r[EAX] + 12 + 0x24));
            W32(kNativeDevice + 0x78c, R32(c.r[EAX] + 12 + 0xec) & 0x100);
            W32(kNativeDevice + 0x790, R32(c.r[EAX] + 12 + 0xd8)); }
        break;
    case D3DF_D3DDevice_SetPixelShaderConstant: ret = 4; break;
    case D3DF_D3DDevice_SetVertexShaderConstant1: case D3DF_D3DDevice_SetVertexShaderConstant4: {
        uint32_t n = fn == D3DF_D3DDevice_SetVertexShaderConstant1 ? 1 : 4;
        if (c.r[ECX] + n > 192) ngb_stop("invalid native vertex constants", c.r[ECX]);
        std::memcpy(HostPtr(kVsConstants + c.r[ECX] * 16, n * 16), HostPtr(c.r[EDX], n * 16), n * 16); break;
    }
    case D3DF_D3DDevice_SetShaderConstantMode:
        W32(kNativeDevice + 8, (R32(kNativeDevice + 8) & ~0x200u) | ((c.r[EAX] & 0x10) ? 0x200 : 0));
        W32(kNativeDevice + 0x1928, c.r[EAX] & ~0x10u); break;
    case D3DF_D3DDevice_CreateVertexBuffer2:
        result = NativeHeader(12); W32(result, 0x01000001); W32(result + 4, NativeData(c.a(0)));
        ret = 4; returns = true; break;
    case D3DF_D3DResource_AddRef:
        result = NativeAddRef(c.a(0)); ret = 4; returns = true; break;
    case D3DF_D3DResource_Release: result = NativeRelease(c.a(0)); ret = 4; returns = true; break;
    case D3DF_D3D_DestroyResource: NativeDestroy(c.r[EDI]); break;
    case D3DF_D3DResource_GetType: {
        uint32_t r = c.r[ECX], t = (R32(r) >> 16) & 7;
        static const uint32_t types[] = {6,7,8,9,3,1,10,0}; result = types[t];
        if (t == 4) result = R32(r + 12) & 4 ? 5 : ((R32(r + 12) >> 4) & 15) == 3 ? 4 : 3;
        returns = true; break;
    }
    case D3DF_D3DDevice_DrawVerticesUP: ret = 16; break;
    case D3DF_D3DDevice_DrawVertices: ret = 4; break;
    case D3DF_D3DDevice_DrawIndexedVertices: ret = 12; break;
    case D3DF_D3DDevice_RunPushBuffer:
        if (c.a(1)) ngb_stop("native push buffer fixups not implemented", c.a(1)); ret = 8; break;
    case D3DF_D3DDevice_End: NativeImmediateEnd(); break;
    case D3DF_D3DDevice_Clear: ret = 24; returns = true; break;
    case D3DF_D3DDevice_CopyRects: ret = 20; returns = true; break;
    case D3DF_D3D_SetFence:
        result = g_backend ? g_backend->Fence() : 0; W32(kNativeDevice + 0x2c, result);
        ret = 4; returns = true; break;
    case D3DF_D3D_BlockOnTime:
        if (g_backend) g_backend->WaitFence(c.a(0)); ret = 8; break;
    case D3DF_D3D_BlockOnResource:
        if (g_backend) {
            uint32_t resource = c.r[EAX], type = R32(resource) & 0x70000;
            g_backend->WaitResource(resource);
            if (type == 0x40000 || type == 0x50000) {
                gpu::TextureDesc d;
                if (gpu::Describe(resource, d)) g_backend->Sync(d.data, gpu::TotalSize(d));
            }
        }
        break;
    case D3DF_D3D_MakeRequestedSpace: case D3DF_D3DDevice_MakeSpace:
        if (c.a(0) > kNativePushBytes - 65536) ngb_stop("native push reservation too large", c.a(0));
        W32(kNativeDevice, native_push); native_read = native_push; result = native_push; ret = 4; returns = true; break;
    case D3DF_CDevice_KickOff: if (g_backend) g_backend->Flush(); break;
    case D3DF_D3DDevice_EndVisibilityTest: {
        uint32_t index = c.r[EAX], page_index = index >> 8;
        if (page_index >= 64) ngb_stop("native visibility index", index);
        uint32_t page = R32(kNativeDevice + 0x7d4 + page_index * 4);
        if (!page) { page = NativePool(4096); W32(kNativeDevice + 0x7d4 + page_index * 4, page); }
        native_last_report = page + (index & 255) * 16;
        std::memset(HostPtr(native_last_report, 16), 0, 16); W32(native_last_report + 12, ~0u);
        if (g_backend) g_backend->VisibilityEnd(native_last_report); returns = true; translate = false; break;
    }
    case D3DF_D3DDevice_BlockUntilVerticalBlank: {
        NativeDiagScope wait_diag(ND_VBLANK_WAIT);
        ngb_graphics_wait_until(native_vblank_due); NativePoll(); break;
    }
    case D3DF_D3DDevice_SetGammaRamp:
        std::memcpy(HostPtr(kNativeDevice + 0x1e04, 768), HostPtr(c.a(1), 768), 768);
        W32(kNativeDevice + 0x240c, 0); W32(kNativeDevice + 0x2404, 1); ret = 8; break;
    case D3DF_Get2DSurfaceDesc:
        NativeSurfaceDesc(c.r[EDI], c.r[EBX], c.r[ESI]); translate = false; break;
    case D3DF_D3D_CommonSetMultiSampleModeAndScale:
        // The host target owns sampling; the guest sees the unscaled render size.
        W32(kNativeDevice + 0x96c, 0x3f800000); W32(kNativeDevice + 0x970, 0x3f800000);
        ret = 4; break;
    case D3DF_D3DDevice_Swap: {
        translate = false;
#ifdef NGB_PLAYER_BUILD
        ngb_switch_frame();
#endif
        uint32_t interval = R32(kRenderState + gpu::kRsPresentationInterval * 4);
        NativeDiagSwap swap_diag(native_frames + 1, interval);
        NativePoll();
        // The display consumer runs independently. Do not turn a 19 ms frame
        // into 33 ms by waiting for the next refresh before recording Present.
        // Keep a 60 fps ceiling for light scenes without locking to vblank.
        swap_diag.Plan(0, native_present_blank, native_vblanks, native_vblanks, false);
        if (uint64_t deadline = native_pacer.Deadline(ngb_elapsed_ns())) {
            swap_diag.WaitBegin(deadline);
            {
                NativeDiagScope wait_diag(ND_PACE);
                ngb_graphics_wait_until(deadline);
            }
            swap_diag.WaitEnd();
            NativePoll();
        }
        native_present_blank = native_vblanks;
        native_pacer.Submitted(ngb_elapsed_ns());
#if defined(NGB_PLAYER_BUILD) && defined(MP_ADD)
        MP_ADD(MP_VK_PRESENT, 0, 0);
#endif
        swap_diag.PresentBegin();
        if (g_backend) {
            NativeDiagScope present_diag(ND_PRESENT);
            g_backend->Present(SurfaceOf(native_back));
        }
        swap_diag.PresentEnd();
        uint32_t back = R32(native_back + 4), front = R32(native_front + 4);
        W32(native_front + 4, back); W32(native_back + 4, front);
        if (g_state.rt.header == native_back) g_state.rt = SurfaceOf(native_back);
        W32(kNativeDevice + 0x2478, ++native_frames);
        W32(kNativeDevice + 0x1dbc + 4, 1);
        uint32_t cb = R32(kNativeDevice + 0x1db4);
        if (cb) {
            NativeDiagScope callback_diag(ND_CALLBACK);
            uint32_t data[] = {native_frames, native_vblanks, 0, 0, 16683};
            std::memcpy(HostPtr(native_callback_data, sizeof data), data, sizeof data);
            ngb_graphics_callback(cb, native_callback_data);
        }
        ngb_pad_flip(); ngb_scene_native_present(native_draws);
        swap_diag.Finish(native_vblanks, native_draws);
        native_completed_draws = native_draws; native_draws = 0;
        NativePoll(); returns = true;
        if (!(native_frames % 120)) std::fprintf(stderr, "[NATIVE-XDK] frames=%u callbacks_pending=%zu original_bodies=0\n", native_frames, native_callbacks.size());
        break;
    }
    case D3DF_CDevice_SetStateVB: ret = 8; break;
    case D3DF_CDevice_SetStateUP:
    case D3DF_D3D_CommonSetDebugRegisters:
    case D3DF_D3D_SetTileNoWait:
    case D3DF_D3DDevice_SetFlickerFilter:
    case D3DF_D3DDevice_PersistDisplay: break;
    default: ngb_stop("unimplemented native D3D API", d3d_funcs[fn].va);
    }
    if (translate) Before(fn, c);
    if (fn == D3DF_D3DDevice_SetRenderTarget) g_state.scissor_count = 0;
    if (fn == D3DF_D3DDevice_SetViewport || fn == D3DF_D3DDevice_SetRenderTarget || fn == D3DF_D3DDevice_SetScreenSpaceOffset)
        NativeViewport();
    if (returns) c.r[EAX] = result;
    c.r[ESP] += 4 + ret;
    return true;
}

bool NativeHelper(uint32_t address, Call c) {
    NativeDiagScope diag(ND_HELPER);
    ++native_helper_calls[address];
    NativeFlush();
    uint32_t ret = 0;
    switch (address) {
    case 0x3c6100: // The title also writes these two fields inline.
        std::memcpy(&g_state.ss_offset_x, HostPtr(kNativeDevice + 0xef8, 4), 4);
        std::memcpy(&g_state.ss_offset_y, HostPtr(kNativeDevice + 0xefc, 4), 4);
        g_state.ss_offset_x -= .53125f; g_state.ss_offset_y -= .53125f;
        NativeViewport(); break; // WriteViewportTransform returns the unchanged PUT
    case 0x3c6300: ret = 4; break; // NV2A CONTROL0: host rasterisation owns this state
    case 0x3c8f10: SyncDeferred(); break;
    case 0x3ca0e0: c.r[EAX] = g_backend && g_backend->Busy(c.r[ECX]); break;
    case 0x3ca170: { // Surface view over a parent texture, data in EAX, parent in EDI
        uint32_t p = NativeHeader(24), parent = c.r[EDI];
        W32(p, 0x01050001); W32(p + 4, c.r[EAX] & 0x0fffffff); W32(p + 12, c.a(0));
        W32(p + 16, c.a(1)); W32(p + 20, parent); NativeAddRef(parent);
        c.r[EAX] = p; ret = 8; break;
    }
    case 0x3c8580: { // GetSurfaceLevel2(texture EAX, level)
        uint32_t parent = c.r[EAX], level = c.a(0); gpu::TextureDesc d;
        if (!gpu::Describe(parent, d) || level >= d.levels) ngb_stop("invalid native surface level", level);
        uint32_t p = NativeHeader(24), format = R32(parent + 12);
        if (!d.linear) for (unsigned shift : {20u, 24u, 28u}) {
            uint32_t n = (format >> shift) & 15;
            format = (format & ~(15u << shift)) | ((n > level ? n - level : 0) << shift);
        }
        W32(p, 0x01050001); W32(p + 4, (d.data + gpu::LevelOffset(d, level)) & 0x0fffffff);
        W32(p + 12, format); W32(p + 16, R32(parent + 16)); W32(p + 20, parent); NativeAddRef(parent);
        c.r[EAX] = p; ret = 4; break;
    }
    case 0x3ca1e0: c.r[EAX] = NativeCreateSurface(c.a(0), c.a(1), c.r[EDX]); ret = 8; break;
    case 0x3ceab0: { // PixelContainer: face/level address, row/slice pitch and subresource header
        uint32_t header = c.a(0), face = c.a(1), level = c.a(2);
        gpu::TextureDesc d;
        if (!gpu::Describe(header, d) || level >= d.levels || face >= (d.cube ? 6u : 1u))
            ngb_stop("invalid native texture subresource", header);
        const auto& f = gpu::Format(d.format);
        uint32_t w = std::max(d.width >> level, 1u), h = std::max(d.height >> level, 1u);
        uint32_t pitch = d.linear ? d.pitch : f.compressed ? std::max((w + 3) / 4, 1u) * f.bits : w * f.bits / 8;
        uint32_t format = R32(header + 12);
        if (!d.linear) {
            format &= 0x000fffff;
            for (unsigned shift : {20u, 24u, 28u}) {
                uint32_t n = (R32(header + 12) >> shift) & 15;
                format |= (n > level ? n - level : 0) << shift;
            }
        }
        W32(c.a(3), d.data + face * gpu::FaceSize(d) + gpu::LevelOffset(d, level));
        W32(c.a(4), pitch); W32(c.a(5), pitch * (f.compressed ? std::max((h + 3) / 4, 1u) : h));
        W32(c.a(6), format); W32(c.a(7), R32(header + 16));
        c.r[EAX] = c.a(5); ret = 32; break;
    }
    case 0x3cecf0:
        c.r[EAX] = NativeTextureHeader(c.r[EAX], c.r[EDX], c.a(0), c.a(1), c.a(2), c.a(3),
                                     c.a(4), c.a(5), c.a(6), c.a(7)); ret = 32; break;
    case 0x3cdc90: NativeDestroyDevice(); break;
    default: ngb_stop("unimplemented native graphics entry", address);
    }
    c.r[ESP] += 4 + ret;
    return true;
}

extern "C" void ngb_d3d_native_report(void) {
    if (!ngb_d3d_native_enabled()) return;
    for (unsigned i = 0; i < D3DF_COUNT; ++i)
        if (native_calls[i]) std::fprintf(stderr, "[NATIVE-API] %08x %llu %s\n", d3d_funcs[i].va,
                                          (unsigned long long)native_calls[i], d3d_funcs[i].name);
    for (auto [address, calls] : native_helper_calls)
        std::fprintf(stderr, "[NATIVE-HELPER] %08x %llu\n", address, (unsigned long long)calls);
}
