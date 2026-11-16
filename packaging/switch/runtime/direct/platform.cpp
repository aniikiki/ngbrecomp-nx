#ifndef NGB_DIAG
#define NGB_DIAG 1
#endif
#include "gpu/backend.h"
#include "nv2a_vk_share.h"

#include <atomic>
#include <mutex>
#include <cstdlib>
#ifdef __SWITCH__
#include <switch.h>
#endif
#include <cstdio>
#include "output.h"
extern "C" {
#include "contiguous.h"
#include "quick_select.h"
void ngb_kernel_log(const char*);
[[noreturn]] void ngb_stop(const char*, uint32_t);
}

// The guest worker owns the standalone Vulkan queue. The Switch frontend
// supplies input and diagnostics separately from the desktop overlays.
extern "C" {
#ifdef NGB_PLAYER_BUILD
#include "../recomp_settings.h"
#endif
int ngb_pc_setting(int which) {
#ifdef NGB_PLAYER_BUILD
    return ngb_switch_setting(which);
#endif
    return which==30;
}
int ngb_2d_screen_flags() { return 0; }
int ngb_2d_stretched() { return 0; }
float ngb_hud_shape() { return 1.0f; } // native Xbox layout inside the scanout
bool nv2a_present_show_fps() { return false; }
int ngb_fps_picture(uint32_t*, size_t, int*, int*, unsigned*) { return 0; }
int ngb_fps_cap(int, float*) { return 0; }
volatile int ngb_fps_target_h, ngb_nv2a_logdraws, nv2a_fps_drawn_outside;
#ifndef NGB_PLAYER_BUILD
int ngb_quick_frozen() { return 0; }
int ngb_quick_layer(uint32_t*) { return 0; }
#endif
int nv2a_dirty_stamp(const void*, size_t, uint64_t*) { return 0; } // hash fallback
void nv2a_quality_get(int* scale, int* aniso, int* shadow, int* msaa)
{
#ifdef NGB_PLAYER_BUILD
    *scale=ngb_switch_setting(0);*aniso=ngb_switch_setting(1);
    *shadow=ngb_switch_setting(2);*msaa=ngb_switch_setting(10);
#else
    *scale = *shadow = *msaa = 1;
    *aniso = 0; // preserve the game's filtering, including single-level textures
#endif
}
int nv2a_vk_share(nv2a_vk_shared*) { return -1; }
void nv2a_vk_queue_lock() {}
void nv2a_vk_queue_unlock() {}
void nv2a_vk_set_draws_off(bool) { ngb_stop("unexpected shared Vulkan device", 0); }
void nv2a_present_set_external(VkImage, uint32_t, uint32_t) { ngb_stop("unexpected external Vulkan surface", 0); }
[[noreturn]] void ngb_renderer_fatal(const char* reason) { ngb_stop(reason, 0); }
uint32_t xbox_HeapAlloc(uint32_t bytes, uint32_t alignment)
{
    return ngb_contiguous_allocate(bytes, 0, UINT32_MAX, alignment, 4);
}
}

namespace {
struct {
    std::atomic<uint64_t> geometry_bytes, reused_bytes, gpu_ns, gpu_buffers, gpu_query_failures;
    std::atomic<uint64_t> sync_ns, record_ns, same_state_pairs, list_pairs, merged_strips, index_hits;
    std::atomic<uint64_t> present_ns, draws, drawn, published;
    std::atomic<uint64_t> queue_ns, fence_ns, publish_ns, descriptors, writes;
} counters;
}

static std::mutex timing_mutex;
static uint64_t render_ns, wait_ns, overlap_ns, edge_ns;
static bool rendering, waiting;
static thread_local bool render_thread;
static std::atomic<int> render_core{-1};
extern "C" void ngb_direct_check_stop(const char* reason, uint32_t detail) {
    if (render_thread) {
        DirectRenderError e{};
        std::snprintf(e.reason, sizeof(e.reason), "%s", reason);
        e.detail = detail;
        throw e;
    }
}
#ifdef __SWITCH__
static std::mutex worker_mutex;
static Thread* sample_worker;
extern "C" void ngb_direct_visit_worker(void (*visit)(void*)) {
    std::lock_guard lock(worker_mutex);
    if (sample_worker) visit(sample_worker);
}
extern "C" void ngb_direct_forget_worker(void) {
    std::lock_guard lock(worker_mutex);
    sample_worker = nullptr;
}
#endif
extern "C" void ngb_direct_render_core(void) {
    render_thread = true;
#ifdef __SWITCH__
    u64 allowed = 0;
    if (R_SUCCEEDED(svcGetInfo(&allowed, InfoType_CoreMask, CUR_PROCESS_HANDLE, 0)) && (allowed & 4))
        svcSetThreadCoreMask(CUR_THREAD_HANDLE, 2, 4);
    render_core = svcGetCurrentProcessorNumber();
    std::lock_guard lock(worker_mutex);
    sample_worker = threadGetSelf();
#endif
}
// Elapsed render work outside an explicit guest wait. Includes driver waits
// and scheduling on both cores, so this is wall-time overlap, not CPU time.
extern "C" void ngb_direct_render_event(int renderer, int active) {
    if (!NGB_DIAG) return;
    std::lock_guard lock(timing_mutex);
    uint64_t now = ngb_elapsed_ns(), dt = now - edge_ns;
    edge_ns = now;
    if (rendering) render_ns += dt;
    if (waiting) wait_ns += dt;
    if (rendering && !waiting) overlap_ns += dt;
    (renderer ? rendering : waiting) = active;
}
extern "C" void ngb_direct_reset_stats(void) {
    std::lock_guard lock(timing_mutex);
    render_ns = wait_ns = overlap_ns = 0;
    rendering = waiting = false;
    edge_ns = ngb_elapsed_ns();
    counters.gpu_ns = counters.gpu_buffers = counters.gpu_query_failures = 0;
    ngb_direct_index_reset();
    counters.geometry_bytes = 0;
    counters.reused_bytes = 0;
    counters.sync_ns = counters.record_ns = counters.same_state_pairs = counters.list_pairs = counters.merged_strips = counters.index_hits = 0;
    counters.present_ns = 0;
    counters.draws = 0;
    counters.drawn = 0;
    counters.published = 0;
    counters.queue_ns = 0;
    counters.fence_ns = 0;
    counters.publish_ns = 0;
    counters.descriptors = 0;
    counters.writes = 0;
}
extern "C" void ngb_direct_draw_time(uint64_t sync_ns, uint64_t record_ns) {
    counters.sync_ns += sync_ns;
    counters.record_ns += record_ns;
}
extern "C" void ngb_direct_draw_pairs(unsigned same_state, unsigned lists, unsigned merged, unsigned index_hits) {
    counters.merged_strips += merged;
    counters.index_hits += index_hits;
    counters.same_state_pairs += same_state;
    counters.list_pairs += lists;
}
extern "C" void ngb_direct_present_time(uint64_t ns, unsigned draws, unsigned drawn, int published)
{
    counters.present_ns += ns;
    counters.draws += draws;
    counters.drawn += drawn;
    counters.published += published;
}
extern "C" void ngb_direct_queue_time(uint64_t ns) { counters.queue_ns += ns; }
extern "C" void ngb_direct_fence_time(uint64_t ns) { counters.fence_ns += ns; }
extern "C" void ngb_direct_publish_time(uint64_t ns) { counters.publish_ns += ns; }
extern "C" void ngb_direct_gpu_time(uint64_t ns, int valid)
{
    if (valid) { counters.gpu_ns += ns; ++counters.gpu_buffers; }
    else ++counters.gpu_query_failures;
}
extern "C" void ngb_direct_geometry_bytes(uint64_t requested, uint64_t reused)
{
    counters.geometry_bytes += requested;
    counters.reused_bytes += reused;
}
extern "C" void ngb_direct_binding_counts(uint64_t requested, uint64_t written)
{
    counters.descriptors += requested;
    counters.writes += written;
}
extern "C" void ngb_direct_stats(void)
{
    char line[200];
    {
        std::lock_guard lock(timing_mutex);
        std::snprintf(line, sizeof(line), "3D scene render_work_ms=%llu guest_wait_ms=%llu render_outside_wait_ms=%llu render_core=%d",
            (unsigned long long)(render_ns / 1000000), (unsigned long long)(wait_ns / 1000000),
            (unsigned long long)(overlap_ns / 1000000), render_core.load());
    }
    ngb_kernel_log(line);
    std::snprintf(line, sizeof(line), "3D scene Direct3D draws=%llu submitted=%llu scanouts=%llu sampled_draw_ms=%llu present_ms=%llu",
        (unsigned long long)counters.draws, (unsigned long long)counters.drawn, (unsigned long long)counters.published,
        (unsigned long long)((counters.sync_ns + counters.record_ns) / 1000000), (unsigned long long)(counters.present_ns / 1000000));
    ngb_kernel_log(line);
    std::snprintf(line, sizeof(line), "3D scene sampled guest sync_us=%llu record_us=%llu adjacent_same_state=%llu list_candidates=%llu fifo_batched_words=%llu",
        (unsigned long long)(counters.sync_ns / 1000), (unsigned long long)(counters.record_ns / 1000),
        (unsigned long long)counters.same_state_pairs, (unsigned long long)counters.list_pairs,
        (unsigned long long)ngb_direct_fifo_batched_words());
    ngb_kernel_log(line);
    ngb_direct_index_report();
    uint64_t compact, indices;
    ngb_direct_index_stats(&compact, &indices);
    std::snprintf(line, sizeof(line), "3D scene native indexed_draws=%llu fifo_indices_omitted=%llu strips_merged=%llu index_cache_hits=%llu",
        (unsigned long long)compact, (unsigned long long)indices, (unsigned long long)counters.merged_strips,
        (unsigned long long)counters.index_hits);
    ngb_kernel_log(line);
    std::snprintf(line, sizeof(line), "3D scene Vulkan queue_ms=%llu fence_wait_ms=%llu publish_ms=%llu descriptor_requests=%llu descriptor_writes=%llu",
        (unsigned long long)(counters.queue_ns / 1000000), (unsigned long long)(counters.fence_ns / 1000000),
        (unsigned long long)(counters.publish_ns / 1000000),
        (unsigned long long)counters.descriptors, (unsigned long long)counters.writes);
    ngb_kernel_log(line);
    std::snprintf(line, sizeof(line), "3D scene GPU command_buffers=%llu gpu_us=%llu query_failures=%llu",
        (unsigned long long)counters.gpu_buffers, (unsigned long long)(counters.gpu_ns / 1000),
        (unsigned long long)counters.gpu_query_failures);
    ngb_kernel_log(line);
    std::snprintf(line, sizeof(line), "3D scene geometry requested_MiB=%llu reused_MiB=%llu",
        (unsigned long long)(counters.geometry_bytes >> 20), (unsigned long long)(counters.reused_bytes >> 20));
    ngb_kernel_log(line);
}
