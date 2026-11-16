#pragma once
#include <stddef.h>
#include <stdint.h>

struct screen_vertex {
    float x, y, z, w;
    uint32_t color;
    float u, v;
};

void ngb_menu_gpu_prepare(void);
void ngb_menu_gpu_enable(void);
int ngb_menu_gpu_overlay(const struct screen_vertex vertices[4], const uint8_t *texture,
                         unsigned tw, unsigned th, uint32_t *target, unsigned stride,
                         unsigned width, unsigned height, int additive);
void ngb_menu_gpu_flush(void);
void ngb_menu_gpu_close(void);
void ngb_menu_gpu_report(void);

/* Both the FIFO and the guest CPU run on the worker owning the GL context. */
extern uintptr_t ngb_menu_dirty_begin, ngb_menu_dirty_end;
static inline void ngb_menu_gpu_sync(const void *ptr, size_t bytes)
{
    uintptr_t begin = (uintptr_t)ptr;
    if (ngb_menu_dirty_end && begin < ngb_menu_dirty_end && bytes &&
        (begin >= ngb_menu_dirty_begin || bytes > ngb_menu_dirty_begin - begin))
        ngb_menu_gpu_flush();
}
