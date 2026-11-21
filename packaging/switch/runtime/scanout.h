#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define NGB_SCAN_W 720u
#define NGB_SCAN_H 480u
void ngb_scanout_reset(void);
void ngb_scanout_mode(uint32_t mode, uint32_t fmt, uint32_t pitch, uint32_t phys);
void ngb_scanout_blank(int enabled);
unsigned ngb_scanout_generation(void);
void ngb_scanout_displayed(void);
unsigned ngb_scanout_display_count(void);
int ngb_scanout_ready(void);
int ngb_scanout_visible(void);
void ngb_scanout_blit(uint32_t *dst, unsigned stride_pixels, unsigned width, unsigned height);
void ngb_scanout_refresh(uint32_t phys);
uint32_t *ngb_scanout_movie_buffer(void);
void ngb_scanout_publish_movie(void);

void ngb_scanout_publish_gpu(void);
int ngb_scanout_is_gpu(void);
int ngb_scanout_is_blank(void);
const uint32_t *ngb_scanout_last_pixels(void);
#ifdef __cplusplus
}
#endif
