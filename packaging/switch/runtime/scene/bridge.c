#include "scene.h"
#ifdef NGB_DIRECT3D
#include "direct/output.h"
#endif
#include "guest_memory.h"
#include "contiguous.h"
#include "menu_gpu.h"
#include "runtime.h"
#include "renderer.h"
#include "present.h"
#include "scanout.h"
#include "kernel/kernel.h"
#include "hw/xbox/nv2a/pgraph/pgraph.h"

struct config g_config = { .display = { .renderer = CONFIG_DISPLAY_RENDERER_OPENGL,
                                        .quality.surface_scale = 1 } };
static NV2AState *device;
static MemoryRegion memory;
static uint32_t pending_primitive;
static unsigned draws, scene_flips;
static uint64_t scene_epoch, vertex_upload_bytes, readback_bytes;
static unsigned readback_count, late_frames;
static struct {
    uint64_t shader_ns, link_ns, file_ns, file_bytes, idle_ns;
    unsigned compiles, links, transfers;
} work;

void ngb_scene_shader_time(int linked, uint64_t ns)
{
    if (linked) { ++work.links; work.link_ns += ns; }
    else { ++work.compiles; work.shader_ns += ns; }
}
void ngb_scene_file_time(size_t bytes, uint64_t ns)
{
    ++work.transfers;
    work.file_bytes += bytes;
    work.file_ns += ns;
}
void ngb_scene_idle_time(uint64_t ns) { work.idle_ns += ns; }
static uint64_t read_ns, begin_ns, end_ns, fifo_epoch, previous_flip, window_start;
static unsigned batch_words, window_flip, window_display;
static uint64_t intervals[120];

/* Measure a rotating sample of actual indexed/array submissions. Results
 * are read only after the driver reports them available. */
#define TIMER_SLOTS 32
static struct {
    GLuint starts[TIMER_SLOTS], ends[TIMER_SLOTS];
    uint64_t issued[TIMER_SLOTS], mask;
    unsigned head, pending, samples, invalid;
    uint64_t ns;
} draw_timer;

static void collect_draw_timers(void)
{
    while (draw_timer.pending) {
        unsigned slot = draw_timer.head;
        GLuint id = draw_timer.ends[slot];
        GLint ready;
        glGetQueryObjectiv(id, GL_QUERY_RESULT_AVAILABLE, &ready);
        if (!ready) break;
        GLuint64 start, end;
        glGetQueryObjectui64v(draw_timer.starts[slot], GL_QUERY_RESULT, &start);
        glGetQueryObjectui64v(id, GL_QUERY_RESULT, &end);
        uint64_t ns = (end - start) & draw_timer.mask;
        if (ns <= ngb_elapsed_ns() - draw_timer.issued[slot]) {
            draw_timer.ns += ns;
            ++draw_timer.samples;
        } else {
            ++draw_timer.invalid;
        }
        draw_timer.head = (draw_timer.head + 1) % TIMER_SLOTS;
        --draw_timer.pending;
    }
}

static int compare_interval(const void *left, const void *right)
{
    uint64_t a = *(const uint64_t *)left, b = *(const uint64_t *)right;
    return (a > b) - (a < b);
}
int ngb_scene_active;
#define PAGE_SHIFT 12
uint8_t ngb_target_pages[0x08000000u >> PAGE_SHIFT];

/* Adjacent surfaces can share a partial page. Drop the flag only when the
 * last such surface is evicted or destroyed. */
static uint32_t target_refs[sizeof(ngb_target_pages)];
void ngb_scene_track_surface(uint32_t address, size_t bytes, int delta)
{
    if (!bytes || address >= memory.size) return;
    bytes = MIN(bytes, memory.size - address);
    unsigned first = address >> PAGE_SHIFT, last = (address + bytes - 1) >> PAGE_SHIFT;
    for (unsigned i = first; i <= last; ++i) {
        assert(delta > 0 || target_refs[i]);
        target_refs[i] += delta;
        ngb_target_pages[i] = target_refs[i] != 0;
    }
}

/* The upper 64 MiB is allocated and accessed through contiguous.c. Lower
 * RAM is also written through direct host mappings, so always recheck it. */
uint8_t ngb_vertex_dirty[sizeof(ngb_target_pages)], ngb_texture_dirty[sizeof(ngb_target_pages)];

void ngb_scene_memory(uint8_t *base, size_t bytes)
{
    ngb_scene_invalidate_vertices();
    memset(ngb_texture_dirty, 1, sizeof(ngb_texture_dirty));
    memory = (MemoryRegion){ .ram_ptr = base, .size = bytes };
}

/* The synchronous Switch FIFO owns notifications, interrupts and semaphores.
 * The renderer runs on that same thread and has no separate PFIFO to wake. */
int nv2a_pace_on;
void nv2a_pace_nop(int begin) { (void)begin; }
void nv2a_pace_release(void) {}
void nv2a_vk_progress(void) {}
void bql_lock(void) {}
void bql_unlock(void) {}
void pfifo_kick(NV2AState *d) { (void)d; }
void nv2a_update_irq(NV2AState *d) { (void)d; }
int64_t qemu_clock_get_ns(QEMUClockType type) { (void)type; return ngb_elapsed_ns(); }
void nv2a_renderer_fatal(const char *reason) { ngb_stop(reason, 0); }

DMAObject nv_dma_load(NV2AState *d, hwaddr address)
{
    (void)d;
    uint32_t words[3];
    const void *desc = ngb_instance_aperture(NGB_PRAMIN_BASE + address, sizeof(words));
    if (!desc) ngb_stop("unmapped 3D DMA descriptor", address);
    memcpy(words, desc, sizeof(words));
    return (DMAObject){ .dma_class = GET_MASK(words[0], NV_DMA_CLASS),
        .dma_target = GET_MASK(words[0], NV_DMA_TARGET),
        .address = (words[2] & NV_DMA_ADDRESS) | GET_MASK(words[0], NV_DMA_ADJUST),
        .limit = words[1] };
}

void *nv_dma_map(NV2AState *d, hwaddr address, hwaddr *length)
{
    DMAObject dma = nv_dma_load(d, address);
    uint32_t physical = dma.address & 0x07ffffff;
    if (physical >= memory.size) ngb_stop("invalid 3D DMA address", physical);
    *length = MIN(dma.limit, memory.size - physical);
    return memory.ram_ptr + physical;
}

hwaddr nv_clip_gpu_tile_blit(NV2AState *d, hwaddr address, hwaddr length)
{
    (void)d;
    return address < memory.size ? MIN(length, memory.size - address) : 0;
}

bool memory_region_test_and_clear_dirty(MemoryRegion *mr, hwaddr address, hwaddr bytes, unsigned client)
{
    if (!bytes || address >= mr->size || bytes > mr->size - address) return false;
    if (client == DIRTY_MEMORY_NV2A_SURF_CPU) {
        return false; /* CPU access sets upload_pending on the overlapping surface. */
    }
    if (address < XBOX_CONTIG_ALLOC_BASE) {
        if (client == DIRTY_MEMORY_NV2A) vertex_upload_bytes += bytes;
        return true;
    }
    uint8_t *pages = client == DIRTY_MEMORY_NV2A ? ngb_vertex_dirty : ngb_texture_dirty;
    size_t first = address >> PAGE_SHIFT;
    size_t count = ((address + bytes - 1) >> PAGE_SHIFT) - first + 1;
    if (!memchr(pages + first, 1, count)) return false;
    memset(pages + first, 0, count);
    if (client == DIRTY_MEMORY_NV2A) vertex_upload_bytes += bytes;
    return true;
}

void memory_region_set_client_dirty(MemoryRegion *mr, hwaddr address, hwaddr bytes, unsigned client)
{
    if (client != DIRTY_MEMORY_NV2A_TEX || !bytes || address >= mr->size || bytes > mr->size - address) return;
    size_t first = address >> PAGE_SHIFT;
    size_t count = ((address + bytes - 1) >> PAGE_SHIFT) - first + 1;
    if (count == 1) {
        ngb_vertex_dirty[first] = ngb_texture_dirty[first] = 1;
    } else {
        memset(ngb_vertex_dirty + first, 1, count);
        memset(ngb_texture_dirty + first, 1, count);
    }
}

static void sync_targets(uint32_t address, size_t bytes, bool may_write)
{
    if (!bytes || address >= memory.size || bytes > memory.size - address) return;
    unsigned first = address >> PAGE_SHIFT, last = (address + bytes - 1) >> PAGE_SHIFT;
    if (first == last) {
        if (!ngb_target_pages[first]) return;
    } else if (!memchr(ngb_target_pages + first, 1, last - first + 1)) return;
    SurfaceBinding *surface;
    QTAILQ_FOREACH(surface, &device->pgraph.gl_renderer_state->surfaces, entry) {
        if (address >= surface->vram_addr + surface->size || address + bytes <= surface->vram_addr) continue;
        pgraph_gl_surface_download_if_dirty(device, surface);
        if (may_write) {
            surface->upload_pending = true;
            surface->draw_time = ++device->pgraph.draw_time;
        }
    }
}

enum NgbPresent ngb_scene_present(uint32_t address, unsigned pitch, void *pixels)
{
#ifdef NGB_DIRECT3D
    return NGB_PRESENT_PENDING; // the Direct3D Swap publishes its completed frame
#else
    return ngb_present_surface(device, address, pitch, pixels);
#endif
}

void ngb_scene_count_readback(size_t bytes, uint64_t elapsed)
{
    read_ns += elapsed;
    ++readback_count;
    readback_bytes += bytes;
}

void ngb_scene_read_targets(uint32_t address, size_t bytes)
{
    sync_targets(address, bytes, false);
}

void ngb_scene_cpu_access(uint32_t address, size_t bytes)
{
    /* XBOX_PTR may hand a scalar helper an eight-byte access reported as
     * one byte. Include its trailing page when monitoring potential writes. */
    if (bytes == 1 && memory.size - address >= 8) bytes = 8;
    sync_targets(address, bytes, true);
    memory_region_set_client_dirty(&memory, address, bytes, DIRTY_MEMORY_NV2A_TEX);
}

void ngb_scene_submit_vertices(uint32_t method, uint32_t *words, unsigned count)
{
#ifdef NGB_DIRECT3D
    return; // the indexed draw was recorded by its Direct3D hook
#endif
    int consumed = pgraph_method(device, 0, method, words[0], words, count, count, false);
    if (consumed != (int)count) ngb_stop("incomplete vertex packet", method);
}

unsigned ngb_scene_submit_state(uint32_t method, uint32_t *words, unsigned count)
{
    int consumed = pgraph_method(device, 0, method, words[0], words, count, 1, true);
    if (consumed < 1 || (unsigned)consumed > count) ngb_stop("invalid state packet", method);
    batch_words += consumed;
    return consumed;
}

void ngb_scene_invalidate_vertices(void)
{
    memset(ngb_vertex_dirty, 1, sizeof(ngb_vertex_dirty));
}

/* Before the first 3D draw, retain hardware state while the boot renderer
 * executes its own draws. These callbacks have no deferred work to flush. */
static void boot_surface(NV2AState *d, bool upload, bool color, bool zeta)
{ (void)d; (void)upload; (void)color; (void)zeta; }
static void boot_reports(NV2AState *d) { (void)d; }
static const PGRAPHRenderer boot_renderer = {
    .ops = { .surface_update = boot_surface, .process_pending_reports = boot_reports }
};

static void submit(uint32_t method, uint32_t value)
{
    pgraph_method(device, 0, method, value, &value, 1, 1, false);
}

static void record_flip(void)
{
    uint64_t now = ngb_elapsed_ns();
    collect_draw_timers();
    intervals[scene_flips-window_flip] = now - previous_flip;
    ++scene_flips;
#ifdef NGB_DIRECT3D
    ngb_direct_timing_flip(scene_flips);
#endif
#if defined(NGB_DIRECT3D) && defined(__SWITCH__)
    ngb_profile_next_frame(scene_flips + 1, draws);
#endif
    if (now - previous_flip > 16666667) ++late_frames;
    previous_flip = now;
    if (scene_flips == 30 || scene_flips % 120 == 0 || now - window_start >= 5000000000ull) {
        char line[200];
#ifdef __SWITCH__
        ngb_scene_log_begin();
#endif
        unsigned count = scene_flips - window_flip;
        unsigned displayed = ngb_scanout_display_count();
        qsort(intervals, count, sizeof(intervals[0]), compare_interval);
        snprintf(line, sizeof(line), "3D scene window frames=%u ms=%llu over_16.67ms=%u p95_us=%llu screen_submits=%u",
                 count, (unsigned long long)((now-window_start)/1000000), late_frames,
                 (unsigned long long)(intervals[(95*count-1)/100]/1000), displayed-window_display);
        window_display = displayed;
        ngb_kernel_log(line);
        window_flip = scene_flips;
        window_start = now;
        late_frames = 0;
        snprintf(line, sizeof(line), "3D scene cumulative fifo_ms=%llu draw_begin_ms=%llu draw_end_ms=%llu read_pixels_ms=%llu state_batched_words=%u",
                 (unsigned long long)((ngb_fifo_time_ns()-fifo_epoch)/1000000),
                 (unsigned long long)(begin_ns/1000000), (unsigned long long)(end_ns/1000000),
                 (unsigned long long)(read_ns/1000000), batch_words);
        ngb_kernel_log(line);
        snprintf(line, sizeof(line), "3D scene GPU sampled_draws=%u total_us=%llu invalid=%u",
                 draw_timer.samples, (unsigned long long)(draw_timer.ns / 1000), draw_timer.invalid);
        ngb_kernel_log(line);
        snprintf(line, sizeof(line), "3D scene compiles=%u compile_ms=%llu links=%u link_ms=%llu file_ops=%u file_KiB=%llu file_ms=%llu idle_ms=%llu",
                 work.compiles, (unsigned long long)(work.shader_ns/1000000),
                 work.links, (unsigned long long)(work.link_ns/1000000), work.transfers,
                 (unsigned long long)(work.file_bytes/1024), (unsigned long long)(work.file_ns/1000000),
                 (unsigned long long)(work.idle_ns/1000000));
        ngb_kernel_log(line);
#ifdef NGB_DIRECT3D
        ngb_direct_stats();
#else
        ngb_present_stats();
#endif
        snprintf(line, sizeof(line), "3D scene transfers readbacks=%u read_MiB=%llu vertex_MiB=%llu",
                 readback_count, (unsigned long long)(readback_bytes >> 20),
                 (unsigned long long)(vertex_upload_bytes >> 20));
        ngb_kernel_log(line);
        snprintf(line, sizeof(line), "3D scene flips=%u draws=%u elapsed_ms=%llu", scene_flips, draws,
                 (unsigned long long)((now - scene_epoch) / 1000000));
        ngb_kernel_log(line);
#ifdef __SWITCH__
        ngb_scene_log_end();
#endif
    }
}

int ngb_scene_method(uint32_t *regs, uint32_t method, uint32_t value, uint32_t constants[][4])
{
    if (!memory.ram_ptr) return 0;
    switch (method) {
    case NV097_FLIP_INCREMENT_WRITE:
        if (device) ++device->pgraph.frame_time;
        if (ngb_scene_active) record_flip();
        return 0;
    case NV097_NO_OPERATION: case NV097_WAIT_FOR_IDLE:
    case NV097_SET_FLIP_READ: case NV097_SET_FLIP_WRITE: case NV097_SET_FLIP_MODULO:
    case NV097_SET_SEMAPHORE_OFFSET: case NV097_BACK_END_WRITE_SEMAPHORE_RELEASE:
        return 0;
    }
    if (!device) {
        device = calloc(1, sizeof(*device));
        if (!device) ngb_stop("3D state allocation failed", sizeof(*device));
        device->vram = &memory;
        device->vram_ptr = memory.ram_ptr;
        pgraph_init(device);
        memcpy(device->pgraph.vsh_constants, constants, sizeof(device->pgraph.vsh_constants));
        device->pgraph.renderer = &boot_renderer;
        pgraph_reg_w(&device->pgraph, NV_PGRAPH_CTX_CONTROL, NV_PGRAPH_CTX_CONTROL_CHID);
        pgraph_reg_w(&device->pgraph, NV_PGRAPH_CTX_CACHE1, NV_KELVIN_PRIMITIVE);
    }
    if (!ngb_scene_active) {
        bool indexed = method == NV097_ARRAY_ELEMENT16 || method == NV097_ARRAY_ELEMENT32 || method == NV097_DRAW_ARRAYS;
        if (indexed || (method == NV097_SET_BEGIN_END && value && value != 6)) {
            ngb_menu_gpu_flush();
            ngb_menu_gpu_close();
#ifndef NGB_DIRECT3D
            nv2a_context_init();
            pgraph_init_thread(device);
#endif
            previous_flip = window_start = scene_epoch = ngb_elapsed_ns();
            fifo_epoch = ngb_fifo_time_ns();
            window_display = ngb_scanout_display_count();
#ifndef NGB_DIRECT3D
            GLint timer_bits = 0;
            glGetQueryiv(GL_TIMESTAMP, GL_QUERY_COUNTER_BITS, &timer_bits);
            if (timer_bits > 0) {
                draw_timer.mask = timer_bits >= 64 ? UINT64_MAX : (UINT64_C(1) << timer_bits) - 1;
                glGenQueries(TIMER_SLOTS, draw_timer.starts);
                glGenQueries(TIMER_SLOTS, draw_timer.ends);
            }
#endif
            ngb_scene_active = 1;
            // Blocking waits poll directly, and queued DPCs bypass this mask.
            // Coalesce periodic device checks only after the first 3D draw.
            ngb_poll_mask = 63;
#ifdef NGB_DIRECT3D
            ngb_contiguous_map_guest_banks(1);
            ngb_direct_reset_stats();
#ifdef __SWITCH__
            ngb_profile_next_frame(1, draws);
#endif
            ngb_kernel_log("3D scene Direct3D Vulkan renderer active");
#else
            if (indexed && pending_primitive) submit(NV097_SET_BEGIN_END, pending_primitive);
            ngb_kernel_log("3D scene renderer active");
            char driver[160];
            snprintf(driver, sizeof(driver), "3D scene GL renderer=%s", (const char *)glGetString(GL_RENDERER));
            ngb_kernel_log(driver);
#endif
        } else if (method == NV097_SET_BEGIN_END) {
            pending_primitive = value;
            return 0;
        } else if (method == NV097_INLINE_ARRAY || method == NV097_CLEAR_SURFACE) {
            return 0;
        }
    }
#ifdef NGB_DIRECT3D
    if (ngb_scene_active) {
        if (method == NV097_SET_BEGIN_END && !value) ++draws;
        // The XDK also uses the two clear values as a callback address
        // and argument for its NO_OPERATION interrupt handler.
        if (method == NV097_SET_ZSTENCIL_CLEAR_VALUE) regs[NV_PGRAPH_ZSTENCILCLEARVALUE / 4] = value;
        if (method == NV097_SET_COLOR_CLEAR_VALUE) regs[NV_PGRAPH_COLORCLEARVALUE / 4] = value;
        return !(method >= NV097_SET_CONTEXT_DMA_NOTIFIES && method <= NV097_SET_CONTEXT_DMA_REPORT && method != 0x18c);
    }
#endif
    if (ngb_scene_active && method == NV097_SET_BEGIN_END) {
        bool sample = !value && draws % 61 == 0 && draw_timer.starts[0] && draw_timer.pending < TIMER_SLOTS;
        if (sample) {
            unsigned slot = (draw_timer.head + draw_timer.pending) % TIMER_SLOTS;
            draw_timer.issued[slot] = ngb_elapsed_ns();
            glQueryCounter(draw_timer.starts[slot], GL_TIMESTAMP);
        }
        uint64_t start = ngb_elapsed_ns();
        submit(method, value);
        if (value) begin_ns += ngb_elapsed_ns() - start;
        else end_ns += ngb_elapsed_ns() - start;
        if (sample) {
            unsigned slot = (draw_timer.head + draw_timer.pending) % TIMER_SLOTS;
            glQueryCounter(draw_timer.ends[slot], GL_TIMESTAMP);
            ++draw_timer.pending;
        }
    } else {
        submit(method, value);
    }
    /* The guest uses the two clear values as the function and argument of
     * its own GPU interrupt callback. Preserve CPU-side MMIO visibility. */
    if (method == NV097_SET_COLOR_CLEAR_VALUE) regs[NV_PGRAPH_COLORCLEARVALUE / 4] = value;
    if (method == NV097_SET_ZSTENCIL_CLEAR_VALUE) regs[NV_PGRAPH_ZSTENCILCLEARVALUE / 4] = value;
    if (method >= NV097_SET_CONTEXT_DMA_NOTIFIES && method <= NV097_SET_CONTEXT_DMA_REPORT && method != 0x18c)
        return 0; /* The bootstrap also owns the DMA descriptor for semaphore release. */
    if (ngb_scene_active && method == NV097_SET_BEGIN_END && !value && ++draws == 100)
        ngb_kernel_log("3D scene completed 100 draws");
    return ngb_scene_active;
}

uint32_t *ngb_scene_constant(unsigned word)
{
    if (!device) return NULL;
    device->pgraph.vsh_constants_dirty[word / 4] = true;
    return &device->pgraph.vsh_constants[word / 4][3 - word % 4];
}

void ngb_scene_close(void)
{
#ifdef NGB_DIRECT3D
    ngb_direct_close();
    ngb_contiguous_map_guest_banks(0);
#endif
    if (device) {
        PGRAPHState *pg = &device->pgraph;
        if (!ngb_scene_active) pg->renderer = &boot_renderer;
        if (ngb_scene_active) {
            ngb_present_close();
            if (draw_timer.starts[0]) {
                glDeleteQueries(TIMER_SLOTS, draw_timer.starts);
                glDeleteQueries(TIMER_SLOTS, draw_timer.ends);
            }
            memset(&draw_timer, 0, sizeof(draw_timer));
        }
        pgraph_destroy(pg);
        for (unsigned i = 0; i < NV2A_VERTEXSHADER_ATTRIBUTES; ++i) g_free(pg->vertex_attributes[i].inline_buffer);
        g_free(pg->scale_buf);
        qemu_mutex_destroy(&pg->renderer_lock);
        qemu_cond_destroy(&pg->framebuffer_released);
        qemu_event_destroy(&pg->sync_complete);
        qemu_event_destroy(&pg->flush_complete);
        qemu_event_destroy(&pg->renderer_switch_complete);
        free(device);
        device = NULL;
        g_nv2a = NULL;
    }
    if (g_nv2a_context_display) glo_context_destroy(g_nv2a_context_display);
    if (g_nv2a_context_render) glo_context_destroy(g_nv2a_context_render);
    g_nv2a_context_display = g_nv2a_context_render = NULL;
    glo_shutdown();
    memory = (MemoryRegion){0};
    memset(target_refs, 0, sizeof(target_refs));
    memset(ngb_target_pages, 0, sizeof(ngb_target_pages));
    vertex_upload_bytes = readback_bytes = readback_count = 0;
    memset(&work, 0, sizeof(work));
    read_ns = begin_ns = end_ns = 0;
    batch_words = window_flip = late_frames = 0;
    pending_primitive = draws = scene_flips = ngb_scene_active = 0;
}
