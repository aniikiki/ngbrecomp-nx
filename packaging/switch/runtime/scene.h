#pragma once
#include <stddef.h>
#include <stdint.h>

/* The guest worker owns the FIFO, guest RAM and the offscreen contexts. */
enum NgbPresent { NGB_PRESENT_FALLBACK, NGB_PRESENT_PENDING, NGB_PRESENT_READY };
enum NgbPresent ngb_scene_present(uint32_t physical, unsigned pitch, void *pixels);
void ngb_scene_discard_present(void);
void ngb_scene_memory(uint8_t *base, size_t bytes);
void ngb_scene_close(void);
int ngb_scene_method(uint32_t *registers, uint32_t method, uint32_t value, uint32_t constants[][4]);
uint32_t *ngb_scene_constant(unsigned word);
void ngb_scene_shader_time(int linked, uint64_t ns);
void ngb_scene_file_time(size_t bytes, uint64_t ns);
void ngb_scene_idle_time(uint64_t ns);
void ngb_scene_count_readback(size_t bytes, uint64_t elapsed);
uint64_t ngb_fifo_time_ns(void);
void ngb_scene_track_surface(uint32_t physical, size_t bytes, int delta);
void ngb_scene_read_targets(uint32_t physical, size_t bytes);
void ngb_scene_submit_vertices(uint32_t method, uint32_t *words, unsigned count);
unsigned ngb_scene_submit_state(uint32_t method, uint32_t *words, unsigned count);
void ngb_scene_invalidate_vertices(void);
void ngb_scene_cpu_access(uint32_t physical, size_t length);
extern int ngb_scene_active;
