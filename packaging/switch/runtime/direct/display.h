#pragma once
#include <stdint.h>

#if defined(NGB_DIRECT3D) && ((defined(__SWITCH__) && defined(NGB_PLAYER_BUILD)) || defined(NGB_DISPLAY_TEST))
#define NGB_GPU_PRESENT 1
#endif

#ifdef __cplusplus
extern "C" {
#endif

enum { NGB_SCREEN_W = 1280, NGB_SCREEN_H = 720 };
typedef struct { unsigned x, y, w, h; } NgbScreenRect;
typedef struct {
    int gpu, blank, standard;
    const uint32_t *cpu_bgra;       /* Xbox-size frame, only for software producers. */
    const uint32_t *overlay_rgba;   /* Premultiplied, pitched in 720p screen pixels. */
    NgbScreenRect rects[3];
    unsigned count;
} NgbScreenFrame;

/* The frontend exclusively owns the window. Release its software framebuffer
 * before opening the swapchain, and close the swapchain before reopening it. */
int ngb_display_pending(void);
int ngb_display_open(void *window);
void ngb_display_close(void);
/* 1 presented, 0 retry, -1 return the window to the software frontend. */
int ngb_display_present(const NgbScreenFrame *frame, uint64_t times_us[3]);

#ifdef __cplusplus
}
#endif
