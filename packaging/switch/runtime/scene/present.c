#include "renderer.h"
#include "present.h"
#include "scanout.h"
#include "runtime.h"
#include <string.h>

/* The guest worker owns this GL context. Snapshot the displayed texture
 * before the game reuses it. Actual guest RAM reads retain their own
 * coherence path, even when a presentation transfer is in flight. */
#define SLOTS 2
#define FRAME_BYTES (NGB_SCAN_W * NGB_SCAN_H * sizeof(uint32_t))
static struct {
    GLuint fbo, buffers[SLOTS];
    GLsync fences[SLOTS];
    bool discard[SLOTS], disabled, have_last;
    unsigned head, count, queued, published, busy;
    uint32_t last_address;
    int last_draw;
    uint64_t elapsed;
} queue;

void ngb_scene_discard_present(void)
{
    queue.have_last = false;
    for (unsigned i = 0; i < SLOTS; ++i) queue.discard[i] = true;
}

static bool collect(void *pixels)
{
    bool ready = false;
    while (queue.count) {
        unsigned i = queue.head;
        GLenum status = glClientWaitSync(queue.fences[i], 0, 0);
        if (status == GL_TIMEOUT_EXPIRED) break;
        if (status == GL_WAIT_FAILED) { queue.disabled = true; break; }
        glDeleteSync(queue.fences[i]);
        queue.fences[i] = NULL;
        queue.head = (i + 1) % SLOTS;
        --queue.count;
        if (queue.discard[i]) continue;
        glBindBuffer(GL_PIXEL_PACK_BUFFER, queue.buffers[i]);
        void *src = glMapBufferRange(GL_PIXEL_PACK_BUFFER, 0, FRAME_BYTES, GL_MAP_READ_BIT);
        if (src) memcpy(pixels, src, FRAME_BYTES);
        bool valid = src && glUnmapBuffer(GL_PIXEL_PACK_BUFFER);
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0);
        if (!valid) { queue.disabled = true; break; }
        ready = true;
    }
    if (ready) ++queue.published;
    return ready;
}

static bool enqueue(PGRAPHGLState *r, SurfaceBinding *s)
{
    unsigned i = (queue.head + queue.count) % SLOTS;
    if (!queue.fbo) {
        glGenFramebuffers(1, &queue.fbo);
        glGenBuffers(SLOTS, queue.buffers);
        for (unsigned n = 0; n < SLOTS; ++n) {
            glBindBuffer(GL_PIXEL_PACK_BUFFER, queue.buffers[n]);
            glBufferData(GL_PIXEL_PACK_BUFFER, FRAME_BYTES, NULL, GL_STREAM_READ);
        }
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0);
    }
    glBindFramebuffer(GL_READ_FRAMEBUFFER, queue.fbo);
    glFramebufferTexture2D(GL_READ_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, s->gl_buffer, 0);
    bool valid = glCheckFramebufferStatus(GL_READ_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE;
    if (valid) {
        GLint row_length;
        glGetIntegerv(GL_PACK_ROW_LENGTH, &row_length);
        glPixelStorei(GL_PACK_ROW_LENGTH, 0);
        glBindBuffer(GL_PIXEL_PACK_BUFFER, queue.buffers[i]);
        glReadPixels(0, 0, NGB_SCAN_W, NGB_SCAN_H, s->fmt.gl_format, s->fmt.gl_type, 0);
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0);
        glPixelStorei(GL_PACK_ROW_LENGTH, row_length);
        queue.fences[i] = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);
        valid = queue.fences[i] != NULL && glGetError() == GL_NO_ERROR;
        if (valid) glFlush();
    }
    glFramebufferTexture2D(GL_READ_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, 0, 0);
    glBindFramebuffer(GL_READ_FRAMEBUFFER, r->gl_framebuffer);
    if (valid) {
        queue.discard[i] = false;
        ++queue.count;
        ++queue.queued;
        queue.have_last = true;
        queue.last_address = s->vram_addr;
        queue.last_draw = s->draw_time;
    }
    return valid;
}

enum NgbPresent ngb_present_surface(NV2AState *d, uint32_t address, unsigned pitch, void *pixels)
{
    SurfaceBinding *s = pgraph_gl_surface_get(d, address);
    if (queue.disabled || !s || !s->color || s->swizzle || !s->draw_dirty || s->upload_pending ||
        s->width < NGB_SCAN_W || s->height < NGB_SCAN_H || s->pitch != pitch ||
        s->fmt.gl_format != GL_BGRA || s->fmt.bytes_per_pixel != 4 || d->pgraph.surface_scale_factor != 1) {
        ngb_scene_discard_present();
        return NGB_PRESENT_FALLBACK;
    }
    uint64_t start = ngb_elapsed_ns();
    bool ready = collect(pixels);
    if (!queue.disabled && (!queue.have_last || queue.last_address != address || queue.last_draw != s->draw_time)) {
        if (queue.count == SLOTS) ++queue.busy;
        else if (!enqueue(d->pgraph.gl_renderer_state, s)) queue.disabled = true;
    }
    queue.elapsed += ngb_elapsed_ns() - start;
    if (queue.disabled) return NGB_PRESENT_FALLBACK;
    return ready ? NGB_PRESENT_READY : NGB_PRESENT_PENDING;
}

void ngb_present_stats(void)
{
    char line[160];
    snprintf(line, sizeof(line), "3D scene display queued=%u published=%u busy_polls=%u cpu_ms=%llu fallback_only=%d",
             queue.queued, queue.published, queue.busy, (unsigned long long)(queue.elapsed/1000000), queue.disabled);
    ngb_kernel_log(line);
}

void ngb_present_close(void)
{
    for (unsigned i = 0; i < SLOTS; ++i) if (queue.fences[i]) glDeleteSync(queue.fences[i]);
    if (queue.fbo) {
        glDeleteBuffers(SLOTS, queue.buffers);
        glDeleteFramebuffers(1, &queue.fbo);
    }
    memset(&queue, 0, sizeof(queue));
}
