#ifdef NGB_PLAYER_BUILD
extern "C" void ngb_switch_frame(void);
#endif
// The title's Direct3D calls as state for the renderer (docs/renderer.md). Ported from
// SCDA-XBERecomp's xdk/d3d8.cpp (see NOTICE) to Ninja Gaiden Black's XDK 5849 D3D8LTCG build:
// its own calling conventions (src/d3d/d3d_funcs.h), vertex programs loaded into the GPU's
// program memory (LoadVertexShader / SelectVertexShader), and pre-recorded index push buffers
// (RunPushBuffer).
//
// NGB_RENDERER=mirror: every call still goes to the recompiled Direct3D (xemu draws and shows the
// game); this keeps a copy of the state and draws it with the renderer as well, for comparing.
#include "gpu/sync_constants.h"
#include "native_diag.h"
#include "native_pacing.h"
#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <memory>
#include <mutex>
#include <unordered_map>

#define D3D_FUNCS_TABLE   // (the names and stack sizes: NGB_D3D_TAKE)
#include "d3d_funcs.h"
#include "gpu/backend.h"
#include "gpu/state.h"
#include "gpu/texture.h"
#ifdef NGB_NATIVE_CONTRACT_TEST
#include "gpu/readback.h"
#include <condition_variable>
#include <thread>
#include <chrono>
#endif
#include "gpu/vertex.h"
#include "kernel/kernel.h"

extern "C" uint32_t xbox_HeapAlloc(uint32_t size, uint32_t align);
extern "C" int ngb_render_threaded;  // src/pc_menu.c reads it: the Multithreaded Renderer is drawing
extern "C" { int ngb_render_threaded = 0; }

#ifdef NGB_DIRECT3D
#include "output.h"
extern "C" uint32_t ngb_native_mesh_enabled;
extern "C" int ngb_d3d_native_enabled(void) {
#ifdef NGB_NATIVE_XDK
    return 1;
#else
    static const bool on = std::getenv("NGB_D3D_NATIVE") && std::strcmp(std::getenv("NGB_D3D_NATIVE"), "0");
    return on;
#endif
}
#endif
using kernel::HostPtr;
using kernel::R32;
using kernel::W32;

namespace {

enum Reg { EAX, ECX, EDX, EBX, ESP, EBP, ESI, EDI };

// the call: registers as the hook saw them, stack arguments above the return address
struct Call {
    uint32_t* r;
    uint32_t a(int i) const { return R32(r[ESP] + 4 + 4 * i); }
    float af(int i) const { uint32_t v = a(i); float f; std::memcpy(&f, &v, 4); return f; }
};

// Direct3D's globals in this build (XbSymbolDatabase's names)
constexpr uint32_t kRenderState = 0x3D83D8;      // D3D__RenderState[166]
constexpr uint32_t kTextureState = 0x3D5D10;     // D3D__TextureState[4][32]
constexpr uint32_t kDevicePtr = 0x3D83C8;       // D3D__pDevice
constexpr uint32_t kVsConstants = 0x3D8678;      // the device's copy of c[0..191], hardware order
constexpr uint32_t kSimpleEncode = 0x3E9278;     // D3D__SimpleRenderStateEncode[92]: each simple state's method

gpu::State g_state;
#ifdef NGB_DIRECT3D
// All guest fibers share one host thread. A nested draw can invalidate a
// ticket; the interrupted call then emits its original packet in full.
uint32_t captured_index_stack;
uint64_t compact_draws, compact_indices;
bool native_mesh_coherent;
uint32_t native_mesh_changed = ~0u;
uint64_t native_mesh_revision;
unsigned native_model_depth;
uint64_t native_mesh_attempts, native_mesh_batches, native_mesh_draws, native_mesh_syncs, native_mesh_reused;
extern uint32_t native_draws;
#include "native_simple.inc"
#endif
// The Switch adapter runs every guest worker as a fiber on one host thread.
#ifndef NGB_DIRECT3D
std::recursive_mutex g_lock;
#endif
std::unique_ptr<gpu::Backend> g_backend;
uint32_t g_vis_index;   // D3DDevice_EndVisibilityTest's index (in eax), for its report slot after the body ran
bool g_mirror = true;
uint32_t guest_header;

std::unordered_map<uint32_t, std::shared_ptr<gpu::VertexShader>> g_vs;
std::unordered_map<uint32_t, std::shared_ptr<gpu::PixelShader>> g_ps;

// CreateVertexShader / CreatePixelShader: the arguments, until the recompiled body wrote the handle
uint32_t g_new_decl, g_new_func, g_new_out;

// the GPU's vertex program memory, 136 instructions of 4 dwords, as LoadVertexShader fills it
uint32_t g_program[136][4];
std::shared_ptr<gpu::VertexShader> g_selected;   // SelectVertexShader's program and declaration

void ViewportConstants(std::array<float, 4>& scale, std::array<float, 4>& offset) {
    auto& v = g_state.viewport;
    float hw = v.w * 0.5f, hh = v.h * 0.5f;
    scale = {hw, -hh, (v.max_z - v.min_z) * g_state.zscale, 0};
    offset = {v.x + g_state.ss_offset_x + hw, v.y + g_state.ss_offset_y + hh, v.min_z * g_state.zscale, 0};
}

#ifdef NGB_DIRECT3D
// The title can write constants inline. Compare the live register file once
// and carry the changed blocks through to the recorder. Registers 58 and 59
// are produced by the viewport, even if guest memory contains other values.
void SyncDrawConstants() {
    constexpr unsigned block = gpu::State::constant_block_bytes;
    constexpr unsigned n = sizeof(g_state.vsc) / block;
    static_assert(block == 8 * sizeof(g_state.vsc[0]) && n < 32 && sizeof(g_state.vsc) % block == 0);
    auto* dst = reinterpret_cast<uint8_t*>(g_state.vsc.data());
    const auto* src = static_cast<const uint8_t*>(HostPtr(kVsConstants));
    static_assert(n == 24);
    // The viewport occupies two registers in block 7. Compare its effective
    // values even when the underlying guest register bank has not changed.
    std::array<std::array<float, 4>, 8> patched;
    std::memcpy(patched.data(), src + 7 * block, block);
    ViewportConstants(patched[58 % 8], patched[59 % 8]);
    uint32_t changes = gpu::SyncConstantRange<0, 7, block>(dst, src);
    if (std::memcmp(dst + 7 * block, patched.data(), block)) {
        std::memcpy(dst + 7 * block, patched.data(), block);
        changes |= 1u << 7;
    }
    changes |= gpu::SyncConstantRange<8, 8, block>(dst, src);
    changes |= gpu::SyncConstantRange<16, 8, block>(dst, src);
    g_state.changed_constant_blocks = changes;
    ++g_state.constants_revision;
}
#endif

void SyncDeferred() {
    NativeDiagScope diag(ND_DEFERRED);
#ifdef NGB_DIRECT3D
    native_mesh_changed = ~0u;
#endif
    // deferred states live in the title's memory, which the inline SetRenderState and
    // SetTextureStageState write; so do the vertex shader constants
    // deferred and complex alike: the XDK keeps every one in D3D__RenderState, and inlined code
    // writes there without any function of ours seeing it
    std::memcpy(g_state.rs.data() + gpu::kRsDeferredFirst,
                HostPtr(kRenderState + gpu::kRsDeferredFirst * 4),
                (gpu::kRsMax - gpu::kRsDeferredFirst) * 4);
    // the simple states too, as SetRenderState keeps them (the device's defaults were set before
    // the hooks saw anything); not the pixel shader's, which SetPixelShader loads from its definition
#ifdef NGB_DIRECT3D
    NativeSyncSimple();
#else
    const auto* methods = static_cast<const uint32_t*>(HostPtr(kSimpleEncode));
    const auto* states = static_cast<const uint32_t*>(HostPtr(kRenderState));
    for (uint32_t i = 0; i < gpu::kRsDeferredFirst; i++) {
        uint32_t method = methods[i] & 0x1FFC;
        if ((method >= 0x300 && method < 0x400) || method == 0x1D78)
            g_state.simple[method >> 2] = states[i];
    }
#endif
    for (int s = 0; s < 4; s++)
        std::memcpy(g_state.tss[s].data(), HostPtr(kTextureState + s * 32 * 4), gpu::kTssBumpEnvMat00 * 4);
#ifdef NGB_DIRECT3D
    SyncDrawConstants();
#else
    std::memcpy(g_state.vsc.data(), HostPtr(kVsConstants), sizeof(g_state.vsc));
#endif
    // fixed function: the transforms (view, projection, texture 0-3, world 0-3 at +0xC60) and the
    // material (+0xF00) are written into the device by inlined code
    uint32_t dev = R32(kDevicePtr);
    if (dev) {
#ifdef NGB_DIRECT3D
        if (ngb_d3d_native_enabled()) {
            // NGB inlines palette unbinding in its own code. The device fields
            // and Common reference bits are authoritative on both sides.
            std::memcpy(g_state.textures.data(), HostPtr(dev + 0xf88), 16);
            std::memcpy(g_state.palettes.data(), HostPtr(dev + 0xf98), 16);
        }
#endif
        for (uint32_t t = 0; t < 10; t++) {
            uint32_t pc = t < 2 ? t + 2 : t < 6 ? t + 14 : t + 250;
            std::memcpy(g_state.transforms[pc].data(), HostPtr(dev + 0xC60 + t * 64), 64);
        }
        std::memcpy(g_state.material.data(), HostPtr(dev + 0xF00), 17 * 4);
    }
}

gpu::Surface SurfaceOf(uint32_t header) {
    gpu::Surface s;
    s.header = header;
    if (header) {
        s.data = R32(header + 4);
        s.format = R32(header + 12);
        s.size = R32(header + 16);
    }
    return s;
}

std::shared_ptr<gpu::VertexShader> ReadVertexShader(uint32_t decl, uint32_t func) {
    auto vs = std::make_shared<gpu::VertexShader>();
    if (decl)
        for (uint32_t i = 0; i < 1024; i++) {
            uint32_t t = R32(decl + i * 4);
            vs->decl.push_back(t);
            if (t == 0xFFFFFFFF) break;
        }
    if (func) {
        uint32_t hdr = R32(func);
        vs->program_type = hdr & 0xFFFF;
        uint32_t n = hdr >> 16;
        for (uint32_t i = 0; i < n * 4; i++) vs->program.push_back(R32(func + 4 + i * 4));
        static const bool vplog = std::getenv("NGB_D3D_VPLOG") != nullptr;   // debugging: where the vertex programs come from
        if (vplog)
            std::fprintf(stderr, "[VP] func %08X n %u first %08X %08X %08X %08X\n", func, n, n ? vs->program[0] : 0,
                         n ? vs->program[1] : 0, n ? vs->program[2] : 0, n ? vs->program[3] : 0);
    }
    gpu::ParseDeclaration(*vs);
    return vs;
}

// These are the game's history-quad and particle submission sites. The history
// texture is allocated by the game and can move when a scene is reloaded.
#ifdef NGB_DIRECT3D
static bool CombatEffectsEnabled() {
    static const bool enabled = [] {
        const char* value = std::getenv("NGB_NATIVE_UT");
        return !value || std::strcmp(value, "0") != 0;
    }();
    return enabled && ngb_d3d_native_enabled();
}

static gpu::CombatEffect CombatEffectUP(Call c) {
    using gpu::CombatEffect;
    if (!CombatEffectsEnabled()) return CombatEffect::None;
    const uint32_t site = R32(c.r[ESP]);
    if (site == 0x0031877b || site == 0x00318bf6)
        return (R32(0xc0611c) & 4) ? CombatEffect::Transparent : CombatEffect::None;
    if (site != 0x00324d8a && site != 0x00324f0a && site != 0x00324fe9)
        return CombatEffect::None;
    if (!(R32(0xc0611c) & 4)) return CombatEffect::None;
    const uint32_t history = R32(0xbb57e0);
    if (!history || c.a(2) != 0xbb5708 || c.a(0) != 6 || c.a(1) != 4 || c.a(3) != 28)
        return CombatEffect::None;
    const uint32_t tex = R32(R32(kDevicePtr) + 0xf88);
    if (tex == history) return CombatEffect::HistoryComposite;
    if (tex && g_state.rt.data && R32(history + 4) == g_state.rt.data)
        return CombatEffect::HistoryCapture;
    return CombatEffect::None;
}
#endif

void Draw(uint32_t prim, uint32_t start, uint32_t count, const uint8_t* indices, bool prepared = false,
          gpu::CombatEffect effect = gpu::CombatEffect::None) {
#ifdef NGB_DIRECT3D
    if (!g_backend) return;
    bool measure = ngb_direct_detail_frame != 0;
    uint64_t start_ns = measure ? ngb_elapsed_ns() : 0;
#endif
    if (!prepared) SyncDeferred();
    static bool nolight = std::getenv("NGB_D3D_NOLIGHT") != nullptr;   // debugging
    if (nolight) g_state.rs[gpu::kRsLighting] = 0;
    static bool nofog = std::getenv("NGB_D3D_NOFOG") != nullptr;       // debugging
    if (nofog) g_state.rs[gpu::kRsFogEnable] = 0;
    static int fogn = std::getenv("NGB_D3D_FOGLOG") ? 1 : 0;
    static uint32_t fog_last[5];
    uint32_t fog_now[5] = { g_state.rs[gpu::kRsFogEnable], g_state.rs[gpu::kRsFogStart], g_state.rs[gpu::kRsFogEnd],
                            g_state.rs[gpu::kRsFogColor], g_state.rs[gpu::kRsFogTableMode] };
    if (fogn > 0 && std::memcmp(fog_now, fog_last, sizeof fog_now)) {
        std::memcpy(fog_last, fog_now, sizeof fog_now);
        float st, en, de;
        std::memcpy(&st, &g_state.rs[gpu::kRsFogStart], 4);
        std::memcpy(&en, &g_state.rs[gpu::kRsFogEnd], 4);
        std::memcpy(&de, &g_state.rs[gpu::kRsFogDensity], 4);
        std::fprintf(stderr, "[D3D] fog table %u start %g end %g density %g color %08X range %u\n",
                     g_state.rs[gpu::kRsFogTableMode], st, en, de, g_state.rs[gpu::kRsFogColor],
                     g_state.rs[gpu::kRsRangeFogEnable]);
    }
#ifdef NGB_DIRECT3D
    uint64_t record_start = measure ? ngb_elapsed_ns() : 0;
#else
    ViewportConstants(g_state.vsc[58], g_state.vsc[59]);
#endif
    if (g_backend) {
        NativeDiagScope diag(ND_RECORD);
#ifdef NGB_DIRECT3D
        if (prepared) {
            g_backend->DrawPrepared(g_state, prim, start, count, indices,
                                    {++native_mesh_revision, native_mesh_changed}, effect);
            native_mesh_changed = 0;
        } else
#endif
            g_backend->Draw(g_state, prim, start, count, indices, nullptr, effect);
    }
#ifdef NGB_DIRECT3D
    if (ngb_d3d_native_enabled()) ++native_draws;
    if (measure) ngb_direct_draw_time(record_start - start_ns, ngb_elapsed_ns() - record_start);
#endif
}

// A pushed index list (RunPushBuffer): BEGIN (0x17FC) with the primitive, then 16-bit index
// pairs (0x1800) or 32-bit indices (0x1808), END (BEGIN 0). Anything else is reported once.
void RunPushBuffer(uint32_t pb, bool prepared = false, gpu::CombatEffect effect = gpu::CombatEffect::None) {
    uint32_t data = R32(pb + 4) | 0x80000000u, size = R32(pb + 0xC);
#ifdef NGB_DIRECT3D
    if (ngb_d3d_native_enabled()) {
        // XDK RunPushBuffer reserves the last word for its return jump. The
        // unpatched value in that slot is not part of the recorded commands.
        if (size < 4 || (size & 3)) ngb_stop("invalid native push buffer size", pb);
        size -= 4;
    }
#endif
    std::vector<uint16_t> idx;
    uint32_t prim = 0;
    for (uint32_t o = 0; o + 4 <= size;) {
        uint32_t h = R32(data + o), count = (h >> 18) & 0x7FF, method = h & 0x1FFC;
        if ((h & 0xE0000003) == 0x20000000 || (h & 3) == 1) break;   // jump or call: not expected
        if (!count) { o += 4; continue; } // legal padding/NOP in preallocated push buffers
#ifdef NGB_DIRECT3D
        if (ngb_d3d_native_enabled() && count > (size - o - 4) / 4) {
#ifdef NGB_NATIVE_PUSH_DIAG
            // Host replay only: preserve the failing packet before the strict stop.
            std::fprintf(stderr, "[PUSH-TRUNCATED] pb=%08x common=%08x data=%08x size=%u allocation=%u offset=%u header=%08x count=%u method=%04x prim=%u indices=%zu\n",
                         pb, R32(pb), data, size, R32(pb + 16), o, h, count, method, prim, idx.size());
            if (size <= 1024 * 1024) {
                if (FILE* dump = std::fopen("failed-push-buffer.bin", "wb")) {
                    std::fwrite(HostPtr(pb, 20), 1, 20, dump);
                    std::fwrite(HostPtr(data, size), 1, size, dump);
                    std::fclose(dump);
                }
            }
#endif
            ngb_stop("truncated native index push buffer", pb);
        }
#endif
        const uint32_t* v = static_cast<const uint32_t*>(HostPtr(data + o + 4));
        if (method == 0x17FC) {
            if (v[0]) {
                prim = v[0];
                idx.clear();
            } else if (prim) {
                Draw(prim, 0, uint32_t(idx.size()), reinterpret_cast<const uint8_t*>(idx.data()), prepared, effect);
                prim = 0;
            }
        } else if (method == 0x1800) {
            // The Xbox and the supported hosts store both packed indices little-endian.
            size_t first = idx.size();
            idx.resize(first + size_t(count) * 2);
            if (count) std::memcpy(idx.data() + first, v, size_t(count) * 4);
        } else if (method == 0x1808) {
            for (uint32_t i = 0; i < count; i++) idx.push_back(uint16_t(v[i]));
        } else {
#ifdef NGB_DIRECT3D
            if (ngb_d3d_native_enabled()) ngb_stop("unsupported native index push method", method);
#endif
            static uint32_t seen[64];
            static int n;
            bool known = false;
            for (int i = 0; i < n; i++) known |= seen[i] == method;
            if (!known && n < 64) {
                seen[n++] = method;
                std::fprintf(stderr, "[D3D] push buffer method %04X x%u not drawn\n", method, count);
            }
        }
        o += 4 + 4 * count;
    }
    // a buffer that ends without END still draws what it began
    if (prim && !idx.empty()) Draw(prim, 0, uint32_t(idx.size()), reinterpret_cast<const uint8_t*>(idx.data()), prepared, effect);
}

// The hooked functions Before does nothing for, found at their first call: those skip g_lock. Taken and
// dropped some 400,000 times a second, it was a tenth of the game thread's time (#69).
std::atomic<bool> g_before_idle[D3DF_COUNT];

// before the call: false to let the recompiled body run (always, mirroring)
bool Before(int fn, Call c) {
    if (unsigned(fn) < D3DF_COUNT && g_before_idle[fn].load(std::memory_order_relaxed)) return false;
#ifndef NGB_DIRECT3D
    std::lock_guard<std::recursive_mutex> lock(g_lock);
#endif
    // a draw's guest stack: the code addresses on it, innermost first, and the map piece object being drawn when
    // the render list walk (sub_00308D50, returning to 0x308D6F) called it (the vertex dump, the section pull)
    // Only the optional draw dumps, ID colours and traces consume the guest stack.
#ifdef NGB_DIRECT3D
    static const bool inspect_stack = std::getenv("NGB_D3D_DUMP") || std::getenv("NGB_D3D_IDVIEW") ||
                                      std::getenv("NGB_TRACE_FILE") || std::getenv("NGB_D3D_STEP");
#else
    constexpr bool inspect_stack = true;
#endif
    if (inspect_stack && (fn == D3DF_D3DDevice_DrawIndexedVertices || fn == D3DF_D3DDevice_DrawVertices ||
                          fn == D3DF_D3DDevice_DrawVerticesUP)) {
        int n = 0;
        gpu::g_draw_node = 0;
        for (uint32_t o = 0; o < 0x400; o += 4) {
#ifdef NGB_DIRECT3D
            // This optional stack walk finds the current map piece. A short
            // committed stack can end before the desktop walk's 1 KiB limit.
            const void* word = DirectPage(c.r[ESP] + o, 4);
            if (!word) break;
            uint32_t v;
            std::memcpy(&v, word, 4);
            if (v == 0x00308D6Fu && !gpu::g_draw_node)
                if (const void* node = DirectPage(c.r[ESP] + o + 4, 4))
                    std::memcpy(&gpu::g_draw_node, node, 4);
#else
            uint32_t v = R32(c.r[ESP] + o);
            if (v == 0x00308D6Fu && !gpu::g_draw_node) gpu::g_draw_node = R32(c.r[ESP] + o + 4);
#endif
            if (v >= 0x11000 && v < 0x37A480 && n < 8) gpu::g_draw_stack[n++] = v;
            if (gpu::g_draw_node && n >= 8) break;
        }
        gpu::g_draw_stack_n = n;
    }
    switch (fn) {
    // render states
    case D3DF_D3DDevice_SetRenderState_Simple:
        g_state.simple[(c.r[ECX] & 0x1FFC) >> 2] = c.r[EDX];
        break;
#define COMPLEX(name, index) case D3DF_D3DDevice_SetRenderState_##name: g_state.rs[index] = c.a(0); break;
    COMPLEX(PSTextureModes, gpu::kRsPsTextureModes)
    COMPLEX(VertexBlend, gpu::kRsVertexBlend)
    COMPLEX(FogColor, gpu::kRsFogColor)
    COMPLEX(FillMode, gpu::kRsFillMode)
    COMPLEX(BackFillMode, gpu::kRsBackFillMode)
    COMPLEX(TwoSidedLighting, gpu::kRsTwoSidedLighting)
    COMPLEX(NormalizeNormals, gpu::kRsNormalizeNormals)
    COMPLEX(ZEnable, gpu::kRsZEnable)
    COMPLEX(StencilEnable, gpu::kRsStencilEnable)
    COMPLEX(StencilFail, gpu::kRsStencilFail)
    COMPLEX(FrontFace, gpu::kRsFrontFace)
    COMPLEX(CullMode, gpu::kRsCullMode)
    COMPLEX(TextureFactor, gpu::kRsTextureFactor)
    COMPLEX(LogicOp, gpu::kRsLogicOp)
    COMPLEX(EdgeAntiAlias, gpu::kRsEdgeAntiAlias)
    COMPLEX(MultiSampleAntiAlias, gpu::kRsMultiSampleAntiAlias)
    COMPLEX(MultiSampleMask, gpu::kRsMultiSampleMask)
    COMPLEX(MultiSampleMode, gpu::kRsMultiSampleMode)
    COMPLEX(MultiSampleRenderTargetMode, gpu::kRsMultiSampleRenderTargetMode)
    COMPLEX(ShadowFunc, gpu::kRsShadowFunc)
    COMPLEX(LineWidth, gpu::kRsLineWidth)
    COMPLEX(SampleAlpha, gpu::kRsSampleAlpha)
    COMPLEX(Dxt1NoiseEnable, gpu::kRsDxt1NoiseEnable)
    COMPLEX(YuvEnable, gpu::kRsYuvEnable)
    COMPLEX(OcclusionCullEnable, gpu::kRsOcclusionCullEnable)
    COMPLEX(StencilCullEnable, gpu::kRsStencilCullEnable)
    COMPLEX(RopZCmpAlwaysRead, gpu::kRsRopZCmpAlwaysRead)
    COMPLEX(RopZRead, gpu::kRsRopZRead)
    COMPLEX(DoNotCullUncompressed, gpu::kRsDoNotCullUncompressed)
#undef COMPLEX

    // texture stage states: (stage eax, type edx, value ecx), BumpEnv (stage eax; type, value),
    // TexCoordIndex (stage esi; value), BorderColor and ColorKeyColor (stage eax, value ebx)
    case D3DF_D3DDevice_SetTextureStageStateNotInline:
        if (c.r[EDX] < gpu::kTssCount) g_state.tss[c.r[EAX] & 3][c.r[EDX]] = c.r[ECX];
        break;
    case D3DF_D3DDevice_SetTextureState_BumpEnv:
        if (c.a(0) >= gpu::kTssBumpEnvMat00 && c.a(0) <= gpu::kTssBumpEnvLOffset)
            g_state.tss[c.r[EAX] & 3][c.a(0)] = c.a(1);
        break;
    case D3DF_D3DDevice_SetTextureState_TexCoordIndex:
        g_state.tss[c.r[ESI] & 3][gpu::kTssTexCoordIndex] = c.a(0);
        break;
    case D3DF_D3DDevice_SetTextureState_BorderColor:
        g_state.tss[c.r[EAX] & 3][gpu::kTssBorderColor] = c.r[EBX];
        break;
    case D3DF_D3DDevice_SetTextureState_ColorKeyColor:
        g_state.tss[c.r[EAX] & 3][gpu::kTssColorKeyColor] = c.r[EBX];
        break;

    // fixed function: SetTransform (type eax, matrix edx), SetLight (index, light), LightEnable
    // (index eax; on)
    case D3DF_D3DDevice_SetTransform: {
        uint32_t t = c.r[EAX];
        if (t < 10) {
            uint32_t pc = t < 2 ? t + 2 : t < 6 ? t + 14 : t + 250;
            std::memcpy(g_state.transforms[pc].data(), HostPtr(c.r[EDX]), 64);
        }
        break;
    }
    case D3DF_D3DDevice_SetLight:
        if (c.a(0) < 8 && c.a(1)) {
            auto& light = g_state.lights[c.a(0)];
            const void* value = HostPtr(c.a(1));
#ifdef NGB_DIRECT3D
            if (!std::memcmp(light.data(), value, sizeof(light))) break;
            ++g_state.lights_revision;
#endif
            std::memcpy(light.data(), value, sizeof(light));
        }
        break;
    case D3DF_D3DDevice_LightEnable:
        if (c.r[EAX] < 8)
            g_state.light_enable = c.a(0) ? g_state.light_enable | 1u << c.r[EAX] : g_state.light_enable & ~(1u << c.r[EAX]);
        break;

    // resources: SetTexture (stage eax; texture), SetPalette (stage eax; palette), SetStreamSource
    // (stream eax, buffer ebx; stride)
    case D3DF_D3DDevice_SetTexture:
        g_state.textures[c.r[EAX] & 3] = c.a(0);
        break;
    case D3DF_D3DDevice_SetPalette:
        g_state.palettes[c.r[EAX] & 3] = c.a(0);
        break;
    case D3DF_D3DDevice_SetStreamSource:
        g_state.streams[c.r[EAX] & 15] = {c.r[EBX], c.a(0)};
        break;

    // shaders
    case D3DF_D3DDevice_CreateVertexShader:
        g_new_decl = c.a(0);
        g_new_func = c.a(1);
        g_new_out = c.a(2);
        break;
    case D3DF_D3DDevice_CreatePixelShader:
        g_new_decl = c.a(0);
        g_new_out = c.a(1);
        break;
    case D3DF_D3DDevice_SetVertexShader: {
        uint32_t h = c.a(0);
        g_state.vs_handle = h;
        g_state.vs = nullptr;
        if (h & 1) {
            auto it = g_vs.find(h);
            if (it != g_vs.end()) g_state.vs = it->second;
        }
        break;
    }
    case D3DF_D3DDevice_LoadVertexShader: {          // (handle eax; address): its program into memory
        auto it = g_vs.find(c.r[EAX]);
        uint32_t at = c.a(0);
        if (it != g_vs.end())
            for (size_t i = 0; i < it->second->program.size() / 4 && at + i < 136; i++)
                std::memcpy(g_program[at + i], &it->second->program[i * 4], 16);
        break;
    }
    case D3DF_D3DDevice_SelectVertexShader: {        // (handle eax, address ebx): run from there
        uint32_t h = c.r[EAX], at = c.r[EBX];
        auto vs = std::make_shared<gpu::VertexShader>();
        auto it = g_vs.find(h);
        if (it != g_vs.end()) {
            vs->decl = it->second->decl;
            vs->inputs = it->second->inputs;
            vs->stream_stride = it->second->stream_stride;
        }
        vs->program_type = 0x2078;
        for (uint32_t i = at; i < 136; i++) {
            vs->program.insert(vs->program.end(), g_program[i], g_program[i] + 4);
            if (g_program[i][3] & 1) break;          // the final instruction
        }
        vs->handle = h;
        g_selected = vs;
        g_state.vs_handle = h | 1;
        g_state.vs = vs;
        break;
    }
    case D3DF_D3DDevice_SetPixelShader: {
        // the handle is the PixelShader object: 12 bytes of header, then its copy of the
        // definition (CreatePixelShader allocates 0xFC and copies 0x3C dwords to +0xC); the
        // game made most of its shaders before the hooks recorded any, so read it from there
        g_state.ps = nullptr;
        uint32_t h = c.r[EAX];
        if (!h) break;
        const uint32_t* def = static_cast<const uint32_t*>(HostPtr(h + 0xC));
        auto& ps = g_ps[h];
        if (!ps || std::memcmp(ps->def, def, sizeof(ps->def)) != 0) {
            ps = std::make_shared<gpu::PixelShader>();
            std::memcpy(ps->def, def, sizeof(ps->def));
            ps->handle = h;
        }
        g_state.ps = ps;
        const uint32_t* d = ps->def;
        auto put = [&](uint32_t method, uint32_t v) { g_state.simple[method >> 2] = v; };
        for (int i = 0; i < 8; i++) {
            put(gpu::kMPsAlphaInputs + i * 4, d[0 + i]);
            put(gpu::kMPsConstant0 + i * 4, d[10 + i]);
            put(gpu::kMPsConstant1 + i * 4, d[18 + i]);
            put(gpu::kMPsAlphaOutputs + i * 4, d[26 + i]);
            put(gpu::kMPsRgbInputs + i * 4, d[34 + i]);
            put(gpu::kMPsRgbOutputs + i * 4, d[45 + i]);
        }
        put(gpu::kMPsFinalAbcd, d[8]);
        put(gpu::kMPsFinalEfgh, d[9]);
        put(gpu::kMPsCompareMode, d[42]);
        put(gpu::kMPsFinalConstant0, d[43]);
        put(gpu::kMPsFinalConstant1, d[44]);
        put(gpu::kMPsCombinerCount, d[53]);
        put(gpu::kMPsDotMapping, d[55]);
        put(gpu::kMPsInputTexture, d[56]);
        g_state.rs[gpu::kRsPsTextureModes] = d[54];
        break;
    }
    case D3DF_D3DDevice_SetPixelShaderConstant: {    // (register ecx; source; count eax)
        uint32_t reg = c.r[ECX], src = c.a(0), n = c.r[EAX];
        for (uint32_t i = 0; i < n && reg + i < 16; i++) std::memcpy(g_state.psc[reg + i].data(), HostPtr(src + i * 16), 16);
        gpu::ApplyPixelConstants(g_state, reg, n);
        break;
    }

    // targets and the viewport
    case D3DF_D3DDevice_SetRenderTarget: {
        if (c.a(0)) g_state.rt = SurfaceOf(c.a(0));
        g_state.zs = SurfaceOf(c.a(1));
        uint32_t w, h;
        gpu::SurfaceSize(g_state.rt, w, h);
        static int rtlog = std::getenv("NGB_D3D_RTLOG") ? 400 : 0;   // debugging: the targets as they are set
        if (rtlog > 0) {
            uint32_t zw = 0, zh = 0;
            gpu::SurfaceSize(g_state.zs, zw, zh);
            if (!c.a(0) || zw != w || zh != h) {
                rtlog--;
                std::fprintf(stderr, "[RT] SetRenderTarget rt %08X (data %08X fmt %08X %ux%u) zs %08X (data %08X fmt %08X %ux%u)\n",
                             c.a(0), g_state.rt.data, g_state.rt.format, w, h, c.a(1), g_state.zs.data, g_state.zs.format, zw, zh);
            }
        }
        g_state.viewport = {0, 0, w, h, 0.0f, 1.0f};
        uint32_t f = g_state.zs.header ? (g_state.zs.format >> 8) & 0xFF : 0x2E;
        g_state.zscale = f == 0x2C || f == 0x30 ? 65535.0f : 16777215.0f;
        break;
    }
    case D3DF_D3DDevice_SetViewport: {
        uint32_t v = c.a(0);
        float mn, mx;
        std::memcpy(&mn, HostPtr(v + 16), 4);
        std::memcpy(&mx, HostPtr(v + 20), 4);
        g_state.viewport = {R32(v), R32(v + 4), R32(v + 8), R32(v + 12), mn, mx};
        static int vplog = std::getenv("NGB_D3D_RTLOG") ? 400 : 0;
        if (vplog > 0 && (g_state.viewport.w <= 256 || !g_state.rt.data)) {
            vplog--;
            std::fprintf(stderr, "[RT] SetViewport %u %u %u %u z %g..%g (rt data %08X)\n", g_state.viewport.x, g_state.viewport.y,
                         g_state.viewport.w, g_state.viewport.h, mn, mx, g_state.rt.data);
        }
        // clamped to the target, as the XDK does: SetRenderTarget sets a 0x7FFFFFFF square
        uint32_t w, h;
        gpu::SurfaceSize(g_state.rt, w, h);
        if (w && h) {
            g_state.viewport.x = std::min(g_state.viewport.x, w);
            g_state.viewport.y = std::min(g_state.viewport.y, h);
            g_state.viewport.w = std::min(g_state.viewport.w, w - g_state.viewport.x);
            g_state.viewport.h = std::min(g_state.viewport.h, h - g_state.viewport.y);
        }
        g_state.scissor_count = 0;
        break;
    }
    case D3DF_D3DDevice_SetScissors:
        g_state.scissor_count = std::min<uint32_t>(c.a(0), 8);
        for (uint32_t i = 0; i < g_state.scissor_count * 4; i++) g_state.scissors[i] = R32(c.a(2) + i * 4);
        break;
    case D3DF_D3DDevice_SetScreenSpaceOffset:
        g_state.ss_offset_x = c.af(0);
        g_state.ss_offset_y = c.af(1);
        static const bool sslog = std::getenv("NGB_D3D_SSLOG") != nullptr;
        if (sslog) {
            static float lx = -1e9f, ly = -1e9f;
            if (g_state.ss_offset_x != lx || g_state.ss_offset_y != ly)
                std::fprintf(stderr, "[D3D] screen space offset %g %g\n", g_state.ss_offset_x, g_state.ss_offset_y);
            lx = g_state.ss_offset_x;
            ly = g_state.ss_offset_y;
        }
        break;

    // drawing: DrawVerticesUP (prim, count, data, stride), DrawIndexedVertices (prim, count,
    // indices), DrawVertices (prim; start ecx, count eax), RunPushBuffer (buffer, fixups)
    case D3DF_D3DDevice_DrawVerticesUP: {
        uint32_t prim = c.a(0), count = c.a(1), data = c.a(2), stride = c.a(3);
        if (!count || !stride || !g_backend) break;
        // stream 0 points at the vertices through a vertex buffer header of ours, its data
        // address a virtual one (Common bit 31, mem::ResourceData)
        auto saved = g_state.streams[0];
        if (!guest_header) guest_header = xbox_HeapAlloc(20, 16);
        W32(guest_header, 0x80000001u);
        W32(guest_header + 4, data);
        g_state.streams[0] = {guest_header, stride};
        gpu::CombatEffect effect = gpu::CombatEffect::None;
#ifdef NGB_DIRECT3D
        effect = CombatEffectUP(c);
#endif
        Draw(prim, 0, count, nullptr, false, effect);
        g_state.streams[0] = saved;
        break;
    }
    case D3DF_D3DDevice_DrawIndexedVertices:
        if (c.a(2)) Draw(c.a(0), 0, c.a(1), static_cast<const uint8_t*>(HostPtr(c.a(2))));
#ifdef NGB_DIRECT3D
        captured_index_stack = g_backend && !g_mirror && ngb_scene_active && c.a(2) && c.a(0) == 6 &&
                               R32(c.r[ESP]) == 0x0030C0B2 ? c.r[ESP] : 0;
#endif
        break;
    case D3DF_D3DDevice_DrawVertices:
        Draw(c.a(0), c.r[ECX], c.r[EAX], nullptr);
        break;
    case D3DF_D3DDevice_RunPushBuffer:
        RunPushBuffer(c.a(0));
        break;

    case D3DF_D3DDevice_Clear: {                     // (count, rects, flags, color, z, stencil)
        if (!g_backend) break;
        const uint8_t* rects = c.a(0) && c.a(1) ? static_cast<const uint8_t*>(HostPtr(c.a(1))) : nullptr;
        g_backend->Clear(g_state, c.a(0), rects, c.a(2), c.a(3), c.af(4), c.a(5));
        break;
    }
    case D3DF_D3DDevice_CopyRects:                   // (source, rects, count, destination, points)
        if (g_backend)
            g_backend->Copy(SurfaceOf(c.a(0)), SurfaceOf(c.a(3)), c.a(2),
                            c.a(1) ? static_cast<const uint8_t*>(HostPtr(c.a(1))) : nullptr,
                            c.a(4) ? static_cast<const uint8_t*>(HostPtr(c.a(4))) : nullptr);
        break;
    case D3DF_D3DDevice_Swap:
        static const bool aspectlog = std::getenv("NGB_ASPECT_LOG") != nullptr;
        if (aspectlog) {   // debugging: the projection's aspect (m22 / m11)
            static unsigned n;
            const auto& m = g_state.transforms[3];
            float m11, m22;
            std::memcpy(&m11, &m[0], 4);
            std::memcpy(&m22, &m[5], 4);
            if (n++ % 120 == 0) std::fprintf(stderr, "[ASPECT] projection m11 %.4f m22 %.4f aspect %.4f\n", m11, m22, m22 / m11);
        }
#ifdef NGB_PLAYER_BUILD
        ngb_switch_frame();
#endif
        if (g_backend) g_backend->Present(g_state.rt);
        break;
    case D3DF_D3DDevice_SetGammaRamp:
        if (g_backend) g_backend->SetGamma(static_cast<const uint8_t*>(HostPtr(c.a(1))));
        break;
    case D3DF_D3DDevice_EndVisibilityTest:
        g_vis_index = c.r[EAX];
        break;
    default:
        if (unsigned(fn) < D3DF_COUNT) g_before_idle[fn].store(true, std::memory_order_relaxed);
        break;
    }
    return false;
}

// after the recompiled body: what it made
void After(int fn, Call c) {
    switch (fn) {   // only these do anything: the rest skip g_lock
    case D3DF_D3DDevice_CreateVertexShader:
    case D3DF_D3DDevice_CreatePixelShader:
    case D3DF_D3DDevice_EndVisibilityTest:
    case D3DF_D3DDevice_Swap:
        break;
    default:
        return;
    }
#ifndef NGB_DIRECT3D
    std::lock_guard<std::recursive_mutex> lock(g_lock);
#endif
    switch (fn) {
    case D3DF_D3DDevice_CreateVertexShader: {
        uint32_t h = g_new_out ? R32(g_new_out) : 0;
        if (h) {
            auto vs = ReadVertexShader(g_new_decl, g_new_func);
            vs->handle = h;
            g_vs[h] = vs;
        }
        break;
    }
    case D3DF_D3DDevice_CreatePixelShader: {
        uint32_t h = g_new_out ? R32(g_new_out) : 0;
        if (h && g_new_decl) {
            auto ps = std::make_shared<gpu::PixelShader>();
            std::memcpy(ps->def, HostPtr(g_new_decl), sizeof(ps->def));
            ps->handle = h;
            g_ps[h] = ps;
        }
        break;
    }
    case D3DF_D3DDevice_SetRenderTarget:             // the default target when the argument was 0
        break;
    case D3DF_D3DDevice_EndVisibilityTest: {
        // its report slot: 16 bytes in the device's pages of them (allocated by the body as needed), where the
        // GPU writes the count; the renderer writes it there instead, once the frame's draws are done
        uint32_t dev = R32(kDevicePtr), page = dev ? R32(dev + 0x7D4 + (g_vis_index >> 8) * 4) : 0;
        if (g_backend && !g_mirror && page) g_backend->VisibilityEnd(page + (g_vis_index & 0xFF) * 16);
        break;
    }
    case D3DF_D3DDevice_Swap:
        // the swap turns the back buffer's surface to the other buffer's memory: the frame's first
        // clear (made before any SetRenderTarget) goes there, not into the picture just shown -- the
        // picture a cut's cross-fade copies at the next frame
        if (g_state.rt.header) g_state.rt = SurfaceOf(g_state.rt.header);
        break;
    default:
        break;
    }
}

extern "C" [[noreturn]] void ngb_renderer_fatal(const char* detail);  // src/ingame_menu.c
extern "C" int ngb_pc_setting(int which);                            // src/ingame_menu.c

bool g_started;
#ifdef NGB_DIRECT3D
// Keep the device and its caches while Sofdec uses the guest framebuffer.
std::unique_ptr<gpu::Backend> prologue_backend;
#endif

void Start() {
    g_started = true;
    const char* e = std::getenv("NGB_RENDERER");
    g_mirror = !e || std::strcmp(e, "d3d") != 0;
#ifndef NGB_DIRECT3D
    g_state = gpu::State{};
#endif
#ifdef NGB_DIRECT3D
    // Preserve the title's startup and movie presenter. Hooks still collect
    // the surfaces, shader handles and state needed for the first 3D draw.
    g_mirror = false;
    if (!ngb_scene_active) return;
    if (prologue_backend) {
        g_backend = std::move(prologue_backend);
        return;
    }
#endif
    g_backend = gpu::CreateBackend();
    if (g_backend && !g_backend->Init(640, 480)) {
        g_backend.reset();
        if (gpu::g_init_retry) {   // the NV2A renderer's device is not up yet: at the next call
            gpu::g_init_retry = false;
            g_started = false;
            return;
        }
        std::fprintf(stderr, "[D3D] renderer init failed\n");
        if (!g_mirror) ngb_renderer_fatal("The renderer could not start on this GPU (details above in the log).");
    }
    // Graphics > Multithreaded Renderer (off by default: for slower CPUs), or NGB_D3D_THREAD=1 or 0 over it; NGB_D3D_THREAD=capture: the
    // renderer draws from a recording of the calls on the title's thread (src/d3d/gpu/threaded.cpp)
    const char* thread = std::getenv("NGB_D3D_THREAD");
    if (g_backend && (thread ? std::strcmp(thread, "0") != 0 : ngb_pc_setting(30) != 0)) {
        g_backend = gpu::CreateThreadedBackend(std::move(g_backend));
        __atomic_store_n(&ngb_render_threaded, 1, __ATOMIC_RELAXED);
        std::fprintf(stderr, "[D3D] drawing from a recording of the calls\n");
    }
    std::fprintf(stderr, "[D3D] renderer on (%s)\n", g_mirror ? "mirroring the NV2A emulation" : "drawing to the window");
}

// Calls that end here, their library body skipped (stage B): what the body would add to the push buffer only feeds
// the NV2A emulation, which draws nothing while this renderer draws. Both below by default since 0.9.57 (8% less
// CPU on a desktop, the pictures as they were in five chapters and the shaders' scenes); NGB_D3D_TAKE=name,name...
// only those, NGB_D3D_TAKE=none none.
// Only these can be taken, each checked in the library's code: its arguments' bytes (its ret n), and why
// skipping it leaves nothing the title or the rest of the library reads
struct Takeable { int fn; uint32_t ret; };
constexpr Takeable kTakeable[] = {
    {D3DF_CDevice_SetStateVB, 8},              // the lazy state flush (sub_003D1E60) and the vertex arrays: methods only
    // (not SetStateUP: it also works out the size of DrawVerticesUP's vertices, device +0xBCC/+0xBD0, for its copy)
    {D3DF_D3DDevice_SetRenderState_Simple, 0}, // two words into the push buffer (the inlined caller keeps the state)
    // (not SetLight and LightEnable: the title reads the device's light table itself, sub_0019E150, for the
    // vertex shader constants of what it lights by hand)
};
uint32_t g_take_ret[D3DF_COUNT];
bool g_take[D3DF_COUNT];

void TakeInit() {
    const char* e = std::getenv("NGB_D3D_TAKE");
    if (!e) e = "CDevice_SetStateVB,D3DDevice_SetRenderState_Simple";
    // (the Multithreaded Renderer too: the library's resource stamps, which its waits read, are SetTexture's,
    // SetPalette's and SetStreamSource's, and the fences SetFence's and the draws'; none of them taken)
    // (nor while the NV2A emulation draws too, unseen, for a comparison: it needs every method)
    if (g_mirror || std::getenv("NGB_D3D_KEEP_NV2A") || !std::strcmp(e, "none")) return;
    for (const Takeable& t : kTakeable) {
        const char* n = d3d_funcs[t.fn].name;
        size_t len = std::strlen(n);
        for (const char* p = e; (p = std::strstr(p, n)); p += len)
            if ((p == e || p[-1] == ',') && (p[len] == ',' || !p[len])) {
                g_take[t.fn] = true;
                g_take_ret[t.fn] = t.ret;
                std::fprintf(stderr, "[D3D] taking %s\n", n);
                break;
            }
    }
}

#ifdef NGB_DIRECT3D
#include "native_device.inc"
#include "native_material.inc"
#ifdef NGB_NATIVE_CONTRACT_TEST
#include "native_contract.inc"
#endif
#endif

}  // namespace

#include "native_diag.inc"

#ifdef NGB_DIRECT3D
namespace {
uint64_t material_frame, material_mode, material_attempts, material_batches;
}
extern "C" { uint32_t ngb_native_material_enabled = 1; }
static bool NativeMaterialEnabled() {
    if (!ngb_d3d_native_enabled()) return 0;
    static const bool encoding_matches = [] {
        const unsigned methods[] = {0x304, 0x340, 0x344, 0x348, 0x368, 0x35c};
        const unsigned states[] = {59, 61, 62, 63, 71, 64};
        for (unsigned j = 0; j < 6; ++j) {
            unsigned matches = 0;
            for (unsigned i = 0; i < gpu::kRsDeferredFirst; ++i)
                if ((R32(kSimpleEncode + i * 4) & 0x1ffc) == methods[j]) {
                    if (i != states[j]) return false;
                    ++matches;
                }
            if (matches != 1) return false;
        }
        return true;
    }();
    if (!encoding_matches) return false;
    static const int mode = [] {
        const char* value = std::getenv("NGB_NATIVE_MATERIAL");
        return value && !std::strcmp(value, "ab") ? 2 : value && !std::strcmp(value, "0") ? 0 : 1;
    }();
    unsigned phase = (native_frames / 8) & 3;
    return mode == 2 ? (phase == 1 || phase == 2) : mode;
}

#include "native_mesh.inc"
extern "C" int ngb_d3d_material_fixed(uint32_t address) {
    material_frame = native_frames + 1;
    material_mode = NativeMaterialEnabled();
    ++material_attempts;
    if (!material_mode) return 0;
    NativeFlush(); NativeDiagScope diag(ND_STATE);
    material::Fixed(address);
    ++material_batches;
    return 1;
}
extern "C" int ngb_d3d_material_texture(unsigned stage, uint32_t address) {
    if (!NativeMaterialEnabled() || stage >= 4) return 0;
    NativeFlush(); NativeDiagScope diag(ND_STATE);
    material::Texture(stage, address);
    return 1;
}
// Used by the isolated host comparison; no per-draw clock or extra SD logging.
extern "C" void ngb_d3d_material_stats(uint64_t out[4]) {
    out[0] = native_frames; out[1] = ngb_native_material_enabled;
    out[2] = ngb_native_material_meshes; out[3] = material_batches;
    ngb_native_material_meshes = 0;
    material_attempts = material_batches = 0;
    // The host ABBA selector runs once per completed frame. The reference
    // helper calls take only an assembly branch, without entering C++ first.
    ngb_native_material_enabled = NativeMaterialEnabled();
}
extern "C" int ngb_direct_index_capture_ready(uint32_t stack) {
    return stack && captured_index_stack == stack && g_take[D3DF_CDevice_SetStateVB];
}
extern "C" int ngb_direct_compact_indices(uint32_t stack, uint32_t count) {
    if (!captured_index_stack || captured_index_stack != stack) return 0;
    captured_index_stack = 0;
    ++compact_draws;
    compact_indices += count;
    return 1;
}
extern "C" void ngb_direct_index_stats(uint64_t* draws, uint64_t* indices) {
    *draws = compact_draws;
    *indices = compact_indices;
}
#endif

extern "C" int d3d_hle_call(int fn, uint32_t regs[8]) {
#ifdef NGB_DIRECT3D
    if (ngb_d3d_native_enabled()) {
        if (unsigned(fn) >= D3DF_COUNT) ngb_stop("invalid native D3D hook", fn);
        return NativeCall(fn, Call{regs});
    }
#endif
    if (!g_started) {
        Start();
        if (g_started) TakeInit();
    }
#ifdef NGB_DIRECT3D
    if (ngb_scene_active && !g_backend) Start();
#endif
    bool took = Before(fn, Call{regs});
    if (!took && g_backend && unsigned(fn) < D3DF_COUNT && g_take[fn]) {
        regs[EAX] = 0;
        regs[ESP] += 4 + g_take_ret[fn];   // its ret n
        took = true;
    }
    return took ? 1 : 0;
}

// after the Swap hook, out of g_lock and the host section (src/d3d/d3d.c): the frame wait (gpu::Backend::FrameWait).
// g_backend is set once, at the first call, by this same thread.
extern "C" void d3d_hle_frame_wait(void) {
    if (g_backend) g_backend->FrameWait();
#ifdef NGB_NATIVE_DIAG
    if (ngb_d3d_native_enabled()) NativeDiagFrame(native_frames);
#endif
}

// D3DDevice_BeginVisibilityTest, inlined into the title (src/d3d/d3d_hooks.c)
extern "C" void d3d_visibility_begin(void) {
#ifdef NGB_DIRECT3D
    // The inline packet is consumed in order with the following API call.
    if (ngb_d3d_native_enabled()) return;
#endif
    if (!g_started) Start();
#ifndef NGB_DIRECT3D
    std::lock_guard<std::recursive_mutex> lock(g_lock);
#endif
    if (g_backend && !g_mirror) g_backend->VisibilityBegin();
}

extern "C" void d3d_hle_after(int fn, const uint32_t regs[8]) {
    if (!g_started) Start();
    After(fn, Call{const_cast<uint32_t*>(regs)});
}

#ifdef NGB_DIRECT3D
extern "C" void ngb_d3d_native_poll(void) {
    if (ngb_d3d_native_enabled()) NativePoll();
}
extern "C" int d3d_hle_native_address(uint32_t address, uint32_t regs[8]) {
    if (!ngb_d3d_native_enabled()) return 0;
    for (unsigned i = 0; i < D3DF_COUNT; ++i)
        if (d3d_funcs[i].va == address) return NativeCall(i, Call{regs});
    return NativeHelper(address, Call{regs});
}
extern "C" void ngb_direct_wait_texture(uint32_t header)
{
    if (g_backend) g_backend->WaitResource(header);
}

extern "C" uint8_t* ngb_direct_lock_prologue_texture(uint32_t header, unsigned width, unsigned height, int* pitch)
{
    gpu::TextureDesc d;
    if (!g_backend || !gpu::Describe(header, d) || d.format != 0x12 || !d.linear ||
        d.width != width || d.height != height || d.pitch < width * 4) return nullptr;
    // The worker may still be uploading this slot from an earlier draw.
    ngb_direct_wait_texture(header);
    *pitch = int(d.pitch);
    return static_cast<uint8_t*>(HostPtr(d.data, gpu::TotalSize(d)));
}

extern "C" void ngb_direct_park_prologue(void)
{
    ngb_direct_finish_put();
    // SetRenderState_Simple can be taken by HLE without emitting FIFO words.
    // Rehydrate the boot compositor from the same XDK table as SyncDeferred.
    const auto* methods = static_cast<const uint32_t*>(HostPtr(kSimpleEncode));
    const auto* states = static_cast<const uint32_t*>(HostPtr(kRenderState));
    for (uint32_t i = 0; i < gpu::kRsDeferredFirst; ++i) {
        uint32_t m = methods[i] & 0x1ffc;
        if ((m >= 0x300 && m < 0x400) || m == 0x1d78)
            ngb_prologue_simple_state(m, states[i]);
    }
    prologue_backend = std::move(g_backend);
    captured_index_stack = 0;
}
extern "C" void ngb_direct_close(void)
{
    captured_index_stack = 0;
    compact_indices = compact_draws = 0;
    ngb_direct_index_close();
    prologue_backend.reset();
    g_backend.reset();
    ngb_render_threaded = 0;
    g_state = gpu::State{};
    g_vs.clear();
    g_ps.clear();
    g_selected.reset();
    std::memset(g_program, 0, sizeof(g_program));
    guest_header = 0;
    g_started = false;
    native_push = native_read = native_lights = native_back = native_front = native_depth = 0;
    native_prim = native_callback = native_last_report = native_draws = native_frames = 0;
    native_scratch = native_scratch_bytes = native_callback_data = native_vblanks = 0;
    native_vblank_due = 0;
    native_flushing = native_polling = false;
    native_callbacks.clear(); native_inline.clear(); native_vertices.clear();
    native_resource_events.clear(); native_current_fn = native_present_blank = 0;
    native_pacer = {};
    native_helper_calls.clear();
    std::memset(native_calls, 0, sizeof native_calls);
}
#endif
