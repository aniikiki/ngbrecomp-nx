// The renderer behind a recording of the title's calls (docs/renderer.md). The title's thread records each call with
// what the console takes at call time -- the state that changed, the resource headers it names, its indices and
// rects, the game's side of it (gpu::Peek) -- and the recording is drawn from: vertex, texture and surface memory are
// read when the draw runs, as the console's GPU reads them after the call returns. Adapted from TGP482's Xbox XBE
// Recomp SDK (runtime/gpu/render_thread.cpp; see NOTICE): the resource headers are kept as copies the renderer reads
// through (gpu/headers.h) instead of copies at other addresses, the game's side and the quick menu travel with the
// calls, and the GPU emulation is what the title waits on: its push buffer is read only as far as the recording has
// been drawn (nv2a_pfifo_gate), so every reference, fence and semaphore the title waits on follows the drawing.
//
// NGB_D3D_THREAD=1: drawn on a thread of its own, the title recording one frame while the one before it draws.
// NGB_D3D_THREAD=capture: each call drawn from its recording at once, on the title's thread (a test of the recording).
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <type_traits>
#include <utility>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <mutex>
#include <thread>

#ifdef NGB_DIRECT3D
#include "output.h"
#ifdef __SWITCH__
#include <pthread.h>
#endif
#else
#include "platform/vcpu.h"   // the title's wait for a frame gives the virtual CPU away meanwhile
#endif
#include <unordered_map>
#include <vector>

#include "gpu/backend.h"
#include "gpu/headers.h"
#include "gpu/vertex.h"
#include "kernel/kernel.h"

extern "C" {
void nv2a_pfifo_gate(int on, uint32_t put);   // xboxrecomp xemu/pfifo.c
uint32_t nv2a_pfifo_put(void);
extern void (*nv2a_user_read_hook)(void);     // xboxrecomp xemu/user.c
}

// NGB_D3D_GATE=0 (a test): the GPU emulation not held back
static void Gate(int on, uint32_t put) {
    static const bool off = std::getenv("NGB_D3D_GATE") && *std::getenv("NGB_D3D_GATE") == '0';
    nv2a_pfifo_gate(off ? 0 : on, put);
}

namespace gpu {
#ifdef NGB_TEXTURE_PRELOAD
extern "C" void ngb_texture_load_idle(Backend*);
#endif

namespace {

// commands handed over at once, so the render thread keeps close behind
constexpr uint32_t kBatchCommands = 64;
constexpr size_t kFreeBatches = 64;   // spare batches kept for reuse
// the render thread, waiting with nothing queued, takes what the title has recorded so far after this long: the
// title may be waiting on memory the GPU emulation writes (a semaphore) behind calls it has not handed over
constexpr auto kIdleTake = std::chrono::microseconds(1500);

// NV2A_PACE_LOG (testing): the hand-overs, every 2 s
struct PaceCounts {
    std::atomic<uint32_t> hook{0}, hook_busy{0}, hook_submit{0}, hook_gate{0}, idle{0}, idle_busy{0}, idle_submit{0},
        batches{0};
    std::atomic<uint64_t> lat_us{0}, lat_max{0}, exec_us{0};
};
static PaceCounts g_pace;
static bool PaceOn() {   // (read late: on Android env.txt is applied after the library is loaded)
    static const bool on = std::getenv("NV2A_PACE_LOG") != nullptr;
    return on;
}
#define g_pace_on PaceOn()
static uint64_t PaceNowUs() {
    return uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
}

enum class Op : uint8_t { State, Headers, Peek, Draw, Clear, Copy, Present, Flush, Gamma, VisBegin, VisEnd };

struct Cmd {
    Op op;
    uint32_t a = 0, b = 0, c = 0, d = 0;
    float f = 0;
    uint32_t data = 0, size = 0;   // bytes in Batch::bytes
    int32_t vs = -1, ps = -1;      // index in Batch::vs / ps: the shader changed
    int32_t quick = -1;            // index in Batch::quick: the frame's quick menu
    Surface s1, s2;
};

// a header copy as sent: data, when the call's own (a DrawVerticesUP's vertices: the title may reuse its memory once
// the call returns), at that offset in the batch's bytes
struct HeaderSend {
    uint32_t addr;
    uint32_t w[5];
    int32_t data = -1;
};

#ifdef NGB_DIRECT3D
struct IndexSnapshot {
    std::vector<uint8_t> bytes;
    IndexBounds bounds{};
};
struct IndexSlot {
    const uint8_t* source = nullptr;
    unsigned count = 0;
    std::shared_ptr<const IndexSnapshot> snapshot;
};
#endif

struct Batch {
#ifdef NGB_DIRECT3D
    std::vector<std::shared_ptr<const IndexSnapshot>> index_snapshots;
#endif
    uint64_t id = 0;
    uint64_t handed_us = 0;   // (NV2A_PACE_LOG)
    uint32_t put = 0;   // the title's DMA_PUT as it was handed over: the push buffer may be read this far once drawn
    std::vector<Cmd> cmds;
    std::vector<uint8_t> bytes;
    std::vector<std::shared_ptr<VertexShader>> vs;
    std::vector<std::shared_ptr<PixelShader>> ps;
    std::vector<QuickPeek> quick;
};

// The plain data in State around its shader pointers, sent as it changes in 64 byte pieces. Of the simple render
// states only those the renderer reads (gpu/state.h's kM...: the pixel shader's combiners, alpha test to depth offset,
// the combiner constants, depth clip control), of the transforms only those drawn with: view and projection (2, 3),
// the textures' (16-19) and the world matrices (256-259).
struct Range {
    size_t off, len;
};
size_t At(const State& s, const void* p) {
    return size_t(static_cast<const uint8_t*>(p) - reinterpret_cast<const uint8_t*>(&s));
}
constexpr auto StateRanges() {
    static_assert(std::is_standard_layout_v<State>);
    auto simple = [](uint32_t first, uint32_t last) {   // methods first to last
        return Range{offsetof(State, simple) + first, size_t(last - first) + 4};
    };
    return std::array{
        simple(kMPsAlphaInputs, kMPsFinalEfgh),
        simple(kMAlphaTestEnable, kMDepthOffset),
        simple(kMPsConstant0, kMPsRgbInputs + 0x1C),
        simple(kMPsCompareMode, kMPsCompareMode),
        simple(kMDepthClipControl, kMDepthClipControl),
        simple(kMPsFinalConstant0, kMPsInputTexture),
        Range{offsetof(State, rs), offsetof(State, index_buffer) - offsetof(State, rs)},          // render states, textures, the streams
        Range{offsetof(State, index_buffer), offsetof(State, vs) - offsetof(State, index_buffer)},
#ifdef NGB_DIRECT3D
        Range{offsetof(State, psc), offsetof(State, transforms) - offsetof(State, psc)},
#else
        Range{offsetof(State, vsc), offsetof(State, transforms) - offsetof(State, vsc)},
#endif            // constants, viewport, surfaces, scissors
        Range{offsetof(State, transforms) + 2 * sizeof(State::transforms[0]), 2 * sizeof(State::transforms[0])},
        Range{offsetof(State, transforms) + 16 * sizeof(State::transforms[0]), 4 * sizeof(State::transforms[0])},
        Range{offsetof(State, transforms) + 256 * sizeof(State::transforms[0]), 4 * sizeof(State::transforms[0])},
#ifdef NGB_DIRECT3D
        Range{offsetof(State, material), sizeof(State::material)},
        Range{offsetof(State, light_enable), offsetof(State, changed_constant_blocks) - offsetof(State, light_enable)},
        Range{offsetof(State, zscale), sizeof(State::zscale)},
#else
        Range{offsetof(State, material), sizeof(State) - offsetof(State, material)},
#endif
    };
}

constexpr auto kStateRanges = StateRanges();

constexpr size_t kPiece = 64;

class Recorded;
std::atomic<Recorded*> g_recorded{nullptr};   // for the title's progress reads (nv2a_user_read_hook)
std::atomic<int> g_hook_busy{0};              // guest threads inside the hook, which the destructor lets out first
#if XBOX_HAS_VCPU
extern "C" void compat_host_enter(void);   // a host section: not parked while holding cap_ (xboxrecomp win32_compat.h)
extern "C" void compat_host_leave(void);
#else
static inline void compat_host_enter(void) {}
static inline void compat_host_leave(void) {}
#endif
// A long wait is logged, never ended: the F1 menu holds the render thread on purpose (present_sdl.c overlay_run),
// and a minimized window or a first shader build can hold it a while too
constexpr int kStallLogSeconds = 10;

class Recorded final : public Backend {
public:
    Recorded(std::unique_ptr<Backend> inner, bool thread) : inner_(std::move(inner)), thread_(thread) {
        cur_ = NewBatch();
        if (thread_) {
            g_recorded.store(this);
            Gate(1, nv2a_pfifo_put());   // what the title put before the first recording: read
            // from guest code (the title polling the GPU's progress): a host section around it, or a guest thread
            // parked here holding cap_ froze the next one to make a Direct3D call (it holds the CPU and g_lock)
            nv2a_user_read_hook = [] {
                g_hook_busy.fetch_add(1);
                compat_host_enter();
                if (Recorded* r = g_recorded.load()) r->TitleWaits();
                compat_host_leave();
                g_hook_busy.fetch_sub(1);
            };
#if defined(NGB_DIRECT3D) && defined(__SWITCH__)
            // libnx normally gives a pthread 128 KiB. This worker now owns
            // Vulkan pipeline creation, formerly on the guest's 2 MiB stack.
            pthread_attr_t attrs;
            int rc = pthread_attr_init(&attrs);
            if (!rc) {
                rc = pthread_attr_setstacksize(&attrs, 2 * 1024 * 1024);
                if (!rc) rc = pthread_create(&native_thread_, &attrs, [](void* self) -> void* {
                    static_cast<Recorded*>(self)->Run();
                    return nullptr;
                }, this);
                pthread_attr_destroy(&attrs);
            }
            if (rc) {
                nv2a_user_read_hook = nullptr;
                g_recorded.store(nullptr);
                nv2a_pfifo_gate(0, 0);
                thread_ = false;
                ngb_kernel_log("3D scene render thread unavailable, drawing synchronously");
            }
#else
            std::thread t([this] { Run(); });
            render_ = t.get_id();
            t.detach();
#endif
        }
    }
    // Only exit() comes here (the game leaves by _exit): the thread is stopped and waited for, so nothing of this is
    // freed under it. A guest thread in the hook is let out first.
    ~Recorded() override {
        if (!thread_) { FreeBatches(); return; }
        nv2a_user_read_hook = nullptr;
        g_recorded.store(nullptr);
        for (int i = 0; g_hook_busy.load(); i++) {   // (a thread held in the hook past 5 s: leaving, not freeing)
            if (i >= 50000) {
                std::fprintf(stderr, "[D3D] a thread still in the progress hook after 5 s: leaving\n");
                std::fflush(nullptr);
                std::_Exit(1);
            }
            std::this_thread::sleep_for(std::chrono::microseconds(100));
        }
        {
            std::lock_guard lock(m_);
            stop_ = true;
        }
        cv_.notify_all();
        nv2a_pfifo_gate(0, 0);
#if defined(NGB_DIRECT3D) && defined(__SWITCH__)
        if (pthread_equal(pthread_self(), native_thread_)) {
#else
        if (std::this_thread::get_id() == render_) {
#endif
            // exit() on the render thread itself (a fatal renderer error, its message already shown): Run never
            // resumes, and the title's thread may be waiting on what this would free -- leaving now
            std::fflush(nullptr);
            std::_Exit(1);
        }
        std::unique_lock lock(m_);
        if (!done_cv_.wait_for(lock, std::chrono::seconds(5), [&] { return exited_; })) {
            // held in a GPU wait that is not ending: the process goes now, as the game's own exit does, rather than
            // free the queue and the renderer under the thread
            std::fprintf(stderr, "[D3D] the render thread did not stop in 5 s: leaving\n");
            std::fflush(nullptr);
            std::_Exit(1);
        }
        lock.unlock();
#if defined(NGB_DIRECT3D) && defined(__SWITCH__)
        pthread_join(native_thread_, nullptr);
#endif
        FreeBatches();
    }

    bool Init(uint32_t width, uint32_t height) override { return inner_->Init(width, height); }

    void Draw(const State& s, uint32_t prim, uint32_t start, uint32_t count, const uint8_t* indices, const IndexBounds*) override {
        std::lock_guard lock(cap_);
#ifdef NGB_DIRECT3D
        const size_t before = cur_->cmds.size();
#endif
        SendState(s, start + count);
#ifdef NGB_DIRECT3D
        if (before == cur_->cmds.size() && before && cur_->cmds.back().op == Op::Draw) {
            ++same_state_pairs_;
            Cmd& prev = cur_->cmds.back();
            if (prim == 6 && prev.a == prim && indices && prev.d == 1 && prev.b == start &&
                TryJoinStrips(s, prev, indices, count)) {
                ++merged_strips_;
                return;
            }
            unsigned width = prim == 5 ? 3 : prim == 2 ? 2 : prim == 1 ? 1 : 0;
            if (width && prev.a == prim && prev.c && count && !(prev.c % width) && !(count % width) &&
                (indices ? prev.d && start == prev.b : !prev.d && uint64_t(prev.b) + prev.c == start))
                ++list_pairs_;
        }
#endif
        Cmd c{Op::Draw};
        c.a = prim;
        c.b = start;
        c.c = count;
        if (indices) {
#ifdef NGB_DIRECT3D
            auto snapshot = CaptureIndices(indices, count);
            if (snapshot) {
                c.d = 2;
                c.size = uint32_t(cur_->index_snapshots.size());
                cur_->index_snapshots.push_back(std::move(snapshot));
            } else
#endif
            {
                c.d = 1;
                c.data = Put(indices, size_t(count) * 2);
            }
        }
        cur_->cmds.push_back(c);
        if (!thread_ || cur_->cmds.size() >= kBatchCommands) Submit();
    }

    void Clear(const State& s, uint32_t count, const uint8_t* rects, uint32_t flags, uint32_t color, float z,
               uint32_t stencil) override {
        std::lock_guard lock(cap_);
        SendState(s, 0);
        Cmd c{Op::Clear};
        c.a = count;
        c.b = flags;
        c.c = color;
        c.d = stencil;
        c.f = z;
        if (count && rects) {
            c.data = Put(rects, size_t(count) * 16);
            c.size = count * 16;
        }
        cur_->cmds.push_back(c);
        if (!thread_) Submit();
    }

    // rects and points are taken now; the copy itself runs in order
    void Copy(const Surface& src, const Surface& dst, uint32_t count, const uint8_t* src_rects,
              const uint8_t* dst_points) override {
        std::lock_guard lock(cap_);
        SendHeader(src.header);
        SendHeader(dst.header);
        FlushHeaders();
        Cmd c{Op::Copy};
        c.a = count;
        c.b = count && src_rects ? Put(src_rects, count * 16) + 1 : 0;     // (offsets + 1: 0 none)
        c.c = count && dst_points ? Put(dst_points, count * 8) + 1 : 0;
        c.s1 = src;
        c.s2 = dst;
        cur_->cmds.push_back(c);
        if (!thread_) Submit();
    }

    void Present(const Surface& front) override {
        uint64_t id;
        {
            std::lock_guard lock(cap_);
#ifdef NGB_DIRECT3D
            ngb_direct_draw_pairs(same_state_pairs_, list_pairs_, merged_strips_, index_hits_);
            same_state_pairs_ = list_pairs_ = merged_strips_ = index_hits_ = 0;
#endif
            SendHeader(front.header);
            FlushHeaders();
            SendPeek(sent_);
            Cmd c{Op::Present};
            c.s1 = front;
            c.quick = int32_t(cur_->quick.size());
            cur_->quick.emplace_back();
            inner_->CaptureQuick(cur_->quick.back());
            cur_->cmds.push_back(c);
            id = Submit();
        }
        // the title records one frame while the one before it draws: the wait for that one in FrameWait, which
        // the hook calls once g_lock and the host section are let go -- the wait gives the virtual CPU away, and
        // another guest thread taking it and then g_lock (a Direct3D call: the in-game menu's) froze the game
        if (thread_) {
            frame_wait_ = last_present_;
            last_present_ = id;
        }
    }
    void FrameWait() override {
        uint64_t id = frame_wait_;
        frame_wait_ = 0;
        if (thread_ && id) Wait(id);
    }

    void Sync(uint32_t data, uint32_t size) override {
        if (!thread_) inner_->Sync(data, size);   // (the renderer writes nothing back to the title's memory)
    }
    void SyncLate(uint32_t data) override {
        if (!thread_) inner_->SyncLate(data);
    }
    void Flush() override {
        std::lock_guard lock(cap_);
        cur_->cmds.push_back(Cmd{Op::Flush});
        Submit();
    }
    void SetGamma(const uint8_t* ramp) override {
        std::lock_guard lock(cap_);
        Cmd c{Op::Gamma};
        c.data = Put(ramp, 768);
        cur_->cmds.push_back(c);
        if (!thread_) Submit();
    }
    void VisibilityBegin() override {
        std::lock_guard lock(cap_);
#ifdef NGB_DIRECT3D
        recording_visibility_ = true;
#endif
        cur_->cmds.push_back(Cmd{Op::VisBegin});
        if (!thread_) Submit();
    }
    void VisibilityEnd(uint32_t report) override {
        std::lock_guard lock(cap_);
#ifdef NGB_DIRECT3D
        recording_visibility_ = false;
#endif
        Cmd c{Op::VisEnd};
        c.a = report;
        cur_->cmds.push_back(c);
        if (!thread_) Submit();
    }

#ifdef NGB_DIRECT3D
    void CheckError() const {
        if (failed_.load(std::memory_order_acquire)) ngb_stop(failure_.reason, failure_.detail);
    }
    void Drain() {
        uint64_t id;
        {
            std::lock_guard lock(cap_);
            id = Submit();
        }
        Wait(id, false);
    }
#endif

    // The title reads the push buffer's progress (it may be waiting on it): what it has recorded since the last
    // batch goes now (Release). Skipped while a call is being recorded.
    void TitleWaits() {
        if (g_pace_on) g_pace.hook++;
        if (!cap_.try_lock()) {
            if (g_pace_on) g_pace.hook_busy++;
            return;
        }
        if (g_pace_on) (cur_->cmds.empty() ? g_pace.hook_gate : g_pace.hook_submit)++;
        Release();
        cap_.unlock();
    }

private:
    void FreeBatches() {
        delete cur_;
        for (Batch* b : free_) delete b;
        for (Batch* b : queue_) delete b;
    }

    Batch* NewBatch() {
        Batch* b;
        {
            std::lock_guard lock(m_);
            if (free_.empty()) {
                b = new Batch;
            } else {
                b = free_.back();
                free_.pop_back();
            }
        }
        b->id = ++next_id_;
        return b;
    }

#ifdef NGB_DIRECT3D
    // Promote a recurring source only on its second use. Pending batches own
    // immutable snapshots; a guest overwrite or a cache collision can't change them.
    std::shared_ptr<const IndexSnapshot> CaptureIndices(const uint8_t* src, unsigned count) {
        if (count < 64 || count > 4096) return {};
        uintptr_t key = reinterpret_cast<uintptr_t>(src);
        auto& slot = index_slots_[((key >> 2) ^ (key >> 13) ^ count) & 2047];
        if (slot.source != src || slot.count != count) {
            slot = {src, count, {}};
            return {};
        }
        size_t bytes = size_t(count)*2;
        if (slot.snapshot && !std::memcmp(slot.snapshot->bytes.data(), src, bytes)) {
            ++index_hits_;
            return slot.snapshot;
        }
        auto copy = std::make_shared<IndexSnapshot>();
        copy->bytes.assign(src, src + bytes);
        copy->bounds = IndexRange(copy->bytes.data(), count);
        slot.snapshot = copy;
        return copy;
    }

    // A repeated last and first index separate the strips. The second strip
    // starts at an even index so face culling sees its original winding.
    bool TryJoinStrips(const State& s, Cmd& prev, const uint8_t* indices, uint32_t count) {
        if (count < 3 || count > 32 || prev.c < 3 || prev.c > 64 || recording_visibility_ ||
            !s.rs[kRsZEnable] || (s.vs_handle & 0xf) == 4 ||
            s.rs[kRsFillMode] == 0x1B00 || s.rs[kRsFillMode] == 0x1B01) return false;
        // Some game passes sample a render target. Keep their per-draw resolves.
        for (uint32_t texture : s.textures) {
            if (!texture) continue;
            const uint32_t data = kernel::R32(texture + 4) & 0x7fffffff;
            if (data == (s.rt.data & 0x7fffffff) || data == (s.zs.data & 0x7fffffff)) return false;
        }
        const size_t end = size_t(prev.data) + prev.c * sizeof(uint16_t);
        if (end != cur_->bytes.size()) return false;
        // Keep the same vertex fetch footprint: joining two sparse strips must
        // not turn them into a dense upload spanning unrelated guest memory.
        auto bounds = [](const uint8_t* src, uint32_t n) {
            std::pair<unsigned, unsigned> range{UINT16_MAX, 0};
            for (uint32_t i = 0; i < n; ++i) {
                uint16_t v;
                std::memcpy(&v, src + 2*i, 2);
                range.first = std::min(range.first, unsigned(v));
                range.second = std::max(range.second, unsigned(v));
            }
            return range;
        };
        auto a = bounds(cur_->bytes.data() + prev.data, prev.c);
        auto b = bounds(indices, count);
        if (a.first > b.second + 1 || b.first > a.second + 1 ||
            a.second - a.first + 1 > 2*prev.c + 64 || b.second - b.first + 1 > 2*count + 64) return false;

        unsigned padding = 2 + (prev.c & 1);
        cur_->bytes.resize(end + 2*(padding + count));
        auto* dest = cur_->bytes.data() + end;
        std::memcpy(dest, dest - 2, 2);
        for (unsigned i = 1; i < padding; ++i) std::memcpy(dest + 2*i, indices, 2);
        std::memcpy(dest + 2*padding, indices, count * 2);
        prev.c += padding + count;
        return true;
    }
#endif

    uint32_t Put(const void* p, size_t n) {
        size_t at = (cur_->bytes.size() + 3) & ~size_t(3);
        cur_->bytes.resize(at + n);
        std::memcpy(cur_->bytes.data() + at, p, n);
        return uint32_t(at);
    }

    // a header as it is now, to the renderer's copies when it changed since it was last sent
    void SendHeader(uint32_t header) {
        if (!header) return;
        HeaderCopy now{};
        // vertex buffer, index buffer and palette headers are 12 bytes: reading 20 can run off the end of the heap
        uint32_t type = kernel::R32(header) & 0x70000;   // 0 vertex, 0x10000 index, 0x30000 palette
        std::memcpy(now.w, kernel::HostPtr(header), type < 0x20000 || type == 0x30000 ? 12 : 20);
        Recent& r = recent_[(header >> 4) & 63];   // the last few, in front of the map (its elements stay put)
        if (r.key != header) r = {header, &sent_headers_[header]};
        if (!std::memcmp(r.copy->w, now.w, sizeof now.w)) return;
        *r.copy = now;
        HeaderSend h{header, {}};
        std::memcpy(h.w, now.w, sizeof h.w);
        pending_headers_.push_back(h);
    }
    struct Recent {
        uint32_t key = 0;
        HeaderCopy* copy = nullptr;
    };
    Recent recent_[64];
    // a vertex buffer of the renderer's own, its data in the title's memory (DrawVerticesUP: Common bit 31): the
    // vertices copied, the copy's header pointing at them
    void SendUpHeader(uint32_t header, uint32_t bytes) {
        HeaderSend h{header, {}};
        std::memcpy(h.w, kernel::HostPtr(header), 12);
        h.data = int32_t(Put(kernel::HostPtr(h.w[1]), bytes));
        std::memset(sent_headers_[header].w, 0, sizeof h.w);   // (always sent: its vertices are new)
        recent_[(header >> 4) & 63] = {};
        pending_headers_.push_back(h);
    }
    void FlushHeaders() {
        if (pending_headers_.empty()) return;
        Cmd c{Op::Headers};
        c.data = Put(pending_headers_.data(), pending_headers_.size() * sizeof(pending_headers_[0]));
        c.size = uint32_t(pending_headers_.size());
        cur_->cmds.push_back(c);
        pending_headers_.clear();
    }

    // the game's side of the call, when it changed
    void SendPeek(const State& s) {
        Peek p;
        std::memset(&p, 0, sizeof p);
        inner_->CapturePeek(s, p);
        if (peek_sent_ && !std::memcmp(&p, &sent_peek_, sizeof p)) return;
        peek_sent_ = true;
        sent_peek_ = p;
        Cmd c{Op::Peek};
        c.data = Put(&p, sizeof p);
        cur_->cmds.push_back(c);
    }

    // a field of the state as the renderer has it, when it differs from what was sent
    void WriteDelta(size_t off, const uint8_t* now, size_t bytes) {
        std::memcpy(reinterpret_cast<uint8_t*>(&sent_) + off, now + off, bytes);
        const uint32_t head[] = {uint32_t(off), uint32_t(bytes)};
        size_t at = cur_->bytes.size();
        cur_->bytes.resize(at + sizeof(head) + bytes);
        std::memcpy(cur_->bytes.data() + at, head, sizeof(head));
        std::memcpy(cur_->bytes.data() + at + sizeof(head), now + off, bytes);
    }

    void SendRange(const uint8_t* now, Range range) {
        const auto* sent = reinterpret_cast<const uint8_t*>(&sent_);
        size_t off = range.off, end = off + range.len;
        while (off < end) {
            size_t group = std::min(end - off, 4 * kPiece);
            if (group > kPiece && !std::memcmp(sent + off, now + off, group)) {
                off += group;
                continue;
            }
            size_t limit = off + group, first = off;
            while (off < limit) {
                size_t n = std::min(limit - off, kPiece);
                if (!std::memcmp(sent + off, now + off, n)) {
                    if (first < off) WriteDelta(first, now, off - first);
                    first = off + n;
                }
                off += n;
            }
            if (first < off) WriteDelta(first, now, off - first);
        }
    }

#ifdef NGB_DIRECT3D
    template<size_t I>
    void SendFixedRange(const uint8_t* now) {
        constexpr Range r = kStateRanges[I];
        const auto* previous = reinterpret_cast<const uint8_t*>(&sent_) + r.off;
        // These fixed-size comparisons fold to direct loads for small fields.
        // Keep the original delta layout on changes, including its group boundaries.
        if (!std::memcmp(previous, now + r.off, r.len)) return;
        if constexpr (r.len <= kPiece) WriteDelta(r.off, now, r.len);
        else SendRange(now, r);
    }
    template<size_t... I>
    void SendFixedRanges(const uint8_t* now, std::index_sequence<I...>) {
        (SendFixedRange<I>(now), ...);
    }
#endif

    // what changed since the last command, in 64 byte pieces; the headers the call names; the game's side.
    // vertices: how many a non-indexed draw reads (a DrawVerticesUP's to copy)
    void SendState(const State& s, uint32_t vertices) {
        title_ = std::this_thread::get_id();
        const uint8_t* now = reinterpret_cast<const uint8_t*>(&s);
        for (int i = 0; i < 4; i++) {
            SendHeader(s.textures[size_t(i)]);
            SendHeader(s.palettes[size_t(i)]);
        }
        for (const auto& st : s.streams) {
            if (!st.vb) continue;
            if (kernel::R32(st.vb) & 0x80000000u)
                SendUpHeader(st.vb, vertices * st.stride);
            else
                SendHeader(st.vb);
        }
        SendHeader(s.rt.header);
        SendHeader(s.zs.header);
        FlushHeaders();
        SendPeek(s);
        Cmd c{Op::State};
        size_t first = cur_->bytes.size();
#ifdef NGB_DIRECT3D
        SendFixedRanges(now, std::make_index_sequence<kStateRanges.size()>{});
#else
        for (const Range& r : kStateRanges) SendRange(now, r);
#endif
#ifdef NGB_DIRECT3D
        const size_t constant_offset = At(s, &s.vsc);
        if (!s.constants_revision || &s != constants_source_ ||
            (s.constants_revision != constants_revision_ && s.constants_revision - constants_revision_ != 1)) {
            SendRange(now, {constant_offset, sizeof(s.vsc)});
        } else if (s.constants_revision != constants_revision_) {
            // SyncDeferred already compared these blocks against the previous draw.
            uint32_t mask = s.changed_constant_blocks;
            while (mask) {
                unsigned first = __builtin_ctz(mask);
                unsigned count = __builtin_ctz(~(mask >> first));
                WriteDelta(constant_offset + first * State::constant_block_bytes, now,
                           count * State::constant_block_bytes);
                mask &= ~(((1u << count) - 1) << first);
            }
        }
        constants_source_ = &s;
        constants_revision_ = s.constants_revision;
        if (!s.lights_revision || &s != light_source_ || s.lights_revision != sent_.lights_revision) {
            SendRange(now, {At(s, &s.lights), sizeof(s.lights)});
            sent_.lights_revision = s.lights_revision;
            light_source_ = &s;
        }
#endif
        if (s.vs.get() != sent_.vs.get()) {
            sent_.vs = s.vs;
            c.vs = int32_t(cur_->vs.size());
            cur_->vs.push_back(s.vs);
        }
        if (s.ps.get() != sent_.ps.get()) {
            sent_.ps = s.ps;
            c.ps = int32_t(cur_->ps.size());
            cur_->ps.push_back(s.ps);
        }
        if (cur_->bytes.size() == first && c.vs < 0 && c.ps < 0) return;
        c.data = uint32_t(first);
        c.size = uint32_t(cur_->bytes.size() - first);
        cur_->cmds.push_back(c);
    }

    // the batch handed over (cap_ held): drawn at once, or queued for the render thread with the title's DMA_PUT
    // as it is now -- every call whose push buffer commands are before it is in this batch or an earlier one (a call
    // is recorded before its Direct3D code writes them)
    uint64_t Submit() {
        uint64_t id = cur_->id;
        if (cur_->cmds.empty() && thread_) return id - 1;
        if (!thread_) {
            const auto* was = g_header_view;
            g_header_view = &headers_;
            ExecuteBatch(*cur_);
            g_header_view = was;
            Recycle(cur_);
            cur_ = NewBatch();
            return id;
        }
        cur_->put = nv2a_pfifo_put();
        if (g_pace_on) cur_->handed_us = PaceNowUs();
        submitted_ = id;
        {
            std::lock_guard lock(m_);
            queue_.push_back(cur_);
        }
        cv_.notify_one();
        cur_ = NewBatch();
        return id;
    }

    // Nothing the title waits on held back (cap_ held): what it has recorded handed over; with nothing recorded or
    // still to draw, the push buffer read as far as the title has put -- every call is recorded before its Direct3D
    // code writes its commands, so whatever is there now belongs to calls already drawn, or to none.
    void Release() {
        if (!cur_->cmds.empty()) {
            Submit();
        } else if (done_.load() >= submitted_) {
            Gate(1, nv2a_pfifo_put());
        }
    }

    // the title waits for a batch drawn (recording), holding no lock (FrameWait). It keeps the virtual CPU
    // (platform/vcpu.h) meanwhile, as before 0.9.40: giving it to the title's other threads (NGB_D3D_WAIT_RELEASE=1,
    // tried for the sound skipping with the drawing behind, #126) made play stutter and answer late, the title
    // waiting for the CPU back every frame. A wait that goes on for kStallLogSeconds is logged, then every so
    // often: a frozen game's log says which frame the render thread is held on.
    void Wait(uint64_t id, bool hand_over = true) {
        if (!id || done_.load() >= id) return;
        if (hand_over && id > submitted_.load()) {   // the batch being recorded: handed over
            std::lock_guard lock(cap_);
            id = Submit();
        }
#if XBOX_HAS_VCPU
        static const bool release = std::getenv("NGB_D3D_WAIT_RELEASE") && *std::getenv("NGB_D3D_WAIT_RELEASE") == '1';
        if (release) vcpu_block_begin();
#endif
#ifdef NGB_DIRECT3D
        ngb_direct_render_event(false, true);
#endif
        {
            std::unique_lock lock(m_);
            auto since = std::chrono::steady_clock::now();
            int logged = 0;
            while (!done_cv_.wait_for(lock, std::chrono::seconds(1), [&] { return done_.load() >= id || exited_; })) {
                int s = int(std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - since).count());
                if (s >= kStallLogSeconds * (logged + 1)) {
                    logged++;
                    std::fprintf(stderr, "[D3D] frame %llu not drawn after %d s: the render thread is held up (drawn %llu)\n",
                                 (unsigned long long)id, s, (unsigned long long)done_.load());
                }
            }
#ifdef NGB_DIRECT3D
            lock.unlock();
            ngb_direct_render_event(false, false);
            CheckError();
#endif
        }
#if XBOX_HAS_VCPU
        if (release) vcpu_block_end();
#endif
    }

    void Recycle(Batch* b) {
#ifdef NGB_DIRECT3D
        b->index_snapshots.clear();
#endif
        b->cmds.clear();
        b->bytes.clear();
        b->vs.clear();
        b->ps.clear();
        b->quick.clear();
        std::lock_guard lock(m_);
        if (free_.size() >= kFreeBatches) {   // a backlog's worth kept, not the peak's for good
            delete b;
            return;
        }
        free_.push_back(b);
    }

    void Run() {
#ifdef NGB_TEXTURE_PRELOAD
        unsigned empty_periods=0;
#endif
        g_header_view = &headers_;
#ifdef NGB_DIRECT3D
        ngb_direct_render_core();
#endif
        for (;;) {
            Batch* b = nullptr;
            {
                std::unique_lock lock(m_);
                if (!cv_.wait_for(lock, kIdleTake, [&] { return stop_ || !queue_.empty(); })) {
                    // nothing handed over for a while: what the title has recorded may be what it waits on
                    lock.unlock();
                    if (g_pace_on) g_pace.idle++;
                    if (cap_.try_lock()) {
                        if (g_pace_on && !cur_->cmds.empty()) g_pace.idle_submit++;
#ifdef NGB_TEXTURE_PRELOAD
                        bool empty=cur_->cmds.empty();
#endif
                        Release();
                        cap_.unlock();
#ifdef NGB_TEXTURE_PRELOAD
                        // Give batched draws priority. Only prepare after sustained inactivity.
                        if(empty && ++empty_periods>=8){empty_periods=0;ngb_texture_load_idle(inner_.get());}
                        if(!empty)empty_periods=0;
#endif
                    } else if (g_pace_on) {
                        g_pace.idle_busy++;
                    }
                    continue;
                }
                if (queue_.empty()) break;
#ifdef NGB_TEXTURE_PRELOAD
                empty_periods=0;
#endif
                b = queue_.front();
                queue_.pop_front();
            }
            uint64_t t0 = g_pace_on ? PaceNowUs() : 0;
#ifdef NGB_DIRECT3D
            ngb_direct_render_event(true, true);
            try {
                ExecuteBatch(*b);
            } catch (const DirectRenderError& error) {
                ngb_direct_render_event(true, false);
                Recycle(b);
                std::lock_guard lock(m_);
                failure_ = error;
                failed_.store(true, std::memory_order_release);
                break;
            }
            ngb_direct_render_event(true, false);
#else
            ExecuteBatch(*b);
#endif
            if (g_pace_on) {
                uint64_t t1 = PaceNowUs(), lat = b->handed_us ? t1 - b->handed_us : 0;
                g_pace.batches++;
                g_pace.exec_us += t1 - t0;
                g_pace.lat_us += lat;
                if (lat > g_pace.lat_max) g_pace.lat_max = lat;
                static uint64_t last = t1;
                if (t1 - last >= 2000000) {
                    last = t1;
                    uint32_t n = g_pace.batches.exchange(0);
                    std::fprintf(stderr, "[PACE] render: %u batches, drawing %.0f ms, handed over to drawn avg %.2f max "
                                 "%.2f ms; title waits %u (lock busy %u, handed %u, gate %u); idle takes %u (lock busy "
                                 "%u, handed %u)\n", n, g_pace.exec_us.exchange(0) / 1000.0,
                                 n ? g_pace.lat_us.exchange(0) / 1000.0 / n : 0, g_pace.lat_max.exchange(0) / 1000.0,
                                 g_pace.hook.exchange(0), g_pace.hook_busy.exchange(0), g_pace.hook_submit.exchange(0),
                                 g_pace.hook_gate.exchange(0), g_pace.idle.exchange(0), g_pace.idle_busy.exchange(0),
                                 g_pace.idle_submit.exchange(0));
                }
            }
            uint64_t id = b->id;
            uint32_t put = b->put;
            Recycle(b);
            Gate(1, put);   // the GPU emulation reads as far as has been drawn
            {
                std::lock_guard lock(m_);
                done_.store(id);
            }
            done_cv_.notify_all();
        }
#if defined(NGB_DIRECT3D) && defined(__SWITCH__)
        ngb_direct_forget_worker();
#endif
        std::lock_guard lock(m_);
        exited_ = true;
        done_cv_.notify_all();
    }

    void ExecuteBatch(Batch& b) {
        for (const Cmd& c : b.cmds) Execute(b, c);
        for (uint32_t a : hosted_) headers_[a].host = nullptr;   // (its bytes go with the batch)
        hosted_.clear();
    }

    void Execute(Batch& b, const Cmd& c) {
        const uint8_t* data = b.bytes.data() + c.data;
        switch (c.op) {
            case Op::State: {
                uint8_t* s = reinterpret_cast<uint8_t*>(&state_);
                for (const uint8_t* p = data; p < data + c.size;) {
                    uint32_t head[2];
                    std::memcpy(head, p, 8);
                    std::memcpy(s + head[0], p + 8, head[1]);
                    p += 8 + head[1];
                }
                if (c.vs >= 0) state_.vs = b.vs[size_t(c.vs)];
                if (c.ps >= 0) state_.ps = b.ps[size_t(c.ps)];
                break;
            }
            case Op::Headers: {
                for (uint32_t i = 0; i < c.size; i++) {
                    HeaderSend h;
                    std::memcpy(&h, data + i * sizeof h, sizeof h);
                    HeaderCopy& to = headers_[h.addr];
                    std::memcpy(to.w, h.w, sizeof to.w);
                    to.host = h.data >= 0 ? b.bytes.data() + h.data : nullptr;
                    if (to.host) hosted_.push_back(h.addr);
                }
                break;
            }
            case Op::Peek: {
                Peek p;
                std::memcpy(&p, data, sizeof p);
                inner_->UsePeek(p);
                break;
            }
            case Op::Draw:
#ifdef NGB_DIRECT3D
                if (c.d == 2) {
                    const auto& snapshot = *b.index_snapshots[c.size];
                    inner_->Draw(state_, c.a, c.b, c.c, snapshot.bytes.data(), &snapshot.bounds);
                    break;
                }
#endif
                inner_->Draw(state_, c.a, c.b, c.c, c.d ? data : nullptr);
                break;
            case Op::Clear: inner_->Clear(state_, c.a, c.size ? data : nullptr, c.b, c.c, c.f, c.d); break;
            case Op::Copy:
                inner_->Copy(c.s1, c.s2, c.a, c.b ? b.bytes.data() + c.b - 1 : nullptr,
                             c.c ? b.bytes.data() + c.c - 1 : nullptr);
                break;
            case Op::Present:
                inner_->UseQuick(b.quick[size_t(c.quick)]);
                inner_->Present(c.s1);
                break;
            case Op::Flush: inner_->Flush(); break;
            case Op::Gamma: inner_->SetGamma(data); break;
            case Op::VisBegin: inner_->VisibilityBegin(); break;
            case Op::VisEnd: inner_->VisibilityEnd(c.a); break;
        }
    }

#ifdef NGB_DIRECT3D
    std::atomic<bool> failed_{};
    DirectRenderError failure_{};
#endif
    std::unique_ptr<Backend> inner_;
#if defined(NGB_DIRECT3D) && defined(__SWITCH__)
    pthread_t native_thread_{};
#endif
    bool thread_;

    // the title's side (cap_: a call being recorded; the render thread takes the batch under it too)
    std::recursive_mutex cap_;
    Batch* cur_ = nullptr;
    std::thread::id title_, render_;
#ifdef NGB_DIRECT3D
    const State* constants_source_ = nullptr;
    uint64_t constants_revision_ = 0;
    unsigned same_state_pairs_ = 0, list_pairs_ = 0, merged_strips_ = 0;
    IndexSlot index_slots_[2048]{};
    unsigned index_hits_ = 0;
    bool recording_visibility_ = false;
    const State* light_source_ = nullptr;
#endif
    State sent_;   // the state as the renderer will have it
    std::unordered_map<uint32_t, HeaderCopy> sent_headers_;
    std::vector<HeaderSend> pending_headers_;
    Peek sent_peek_;
    bool peek_sent_ = false;
    uint64_t next_id_ = 0, last_present_ = 0, frame_wait_ = 0;
    std::atomic<uint64_t> submitted_{0};   // the last batch handed over

    // the renderer's side
    State state_;
    std::unordered_map<uint32_t, HeaderCopy> headers_;
    std::vector<uint32_t> hosted_;   // headers whose data is in the batch being drawn: let go with it

    std::mutex m_;
    std::condition_variable cv_, done_cv_;
    std::deque<Batch*> queue_;
    std::vector<Batch*> free_;
    std::atomic<uint64_t> done_{0};
    bool stop_ = false, exited_ = false;
};

}  // namespace

#ifdef NGB_DIRECT3D
extern "C" void ngb_direct_check_render_error(void) {
    if (Recorded* r = g_recorded.load()) r->CheckError();
}
extern "C" void ngb_direct_finish_put(void) {
    if (Recorded* r = g_recorded.load()) r->Drain();
}
#endif

std::unique_ptr<Backend> CreateThreadedBackend(std::unique_ptr<Backend> inner) {
    const char* e = std::getenv("NGB_D3D_THREAD");
    bool thread = !(e && !std::strcmp(e, "capture"));
    return std::make_unique<Recorded>(std::move(inner), thread);
}

}  // namespace gpu
