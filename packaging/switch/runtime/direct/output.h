#pragma once
#include <stdint.h>
#ifdef __cplusplus
struct DirectRenderError { char reason[160]; uint32_t detail; };
extern "C" {
[[noreturn]] void ngb_stop(const char*, uint32_t);
#endif
extern int ngb_scene_active;
int ngb_d3d_native_enabled(void);
int ngb_d3d_native_entry(uint32_t address);
int ngb_d3d_material_fixed(uint32_t address);
int ngb_d3d_material_texture(unsigned stage, uint32_t address);
void ngb_d3d_material_stats(uint64_t out[4]);
void ngb_d3d_mesh_stats(uint64_t out[8]);
unsigned ngb_d3d_model_suspend(void);
void ngb_d3d_model_resume(unsigned depth);
extern uint64_t ngb_native_material_meshes;
void ngb_d3d_native_poll(void);
void ngb_d3d_native_report(void);
void ngb_scene_native_start(void);
void ngb_scene_native_present(unsigned draws);
uint32_t ngb_graphics_pool_alloc(uint32_t bytes);
void ngb_graphics_pool_free(uint32_t address);
void ngb_graphics_callback(uint32_t routine, uint32_t argument);
uint32_t ngb_graphics_guest_call(uint32_t routine, const uint32_t *arguments, unsigned count);
void ngb_graphics_wait_until(uint64_t nanoseconds);
void ngb_scanout_direct(const void *bgra);
int ngb_prepare_title_device(void);
int ngb_stop_requested(void);
/* A zero total is the ordinary splash. The cache has no count until its recipes are read. */
#define NGB_LOADING_READ_CACHE UINT32_MAX
typedef struct { uint32_t ready, total; } NgbLoadingProgress;
void ngb_loading_set_progress(uint32_t ready, uint32_t total);
NgbLoadingProgress ngb_loading_progress(void);
void ngb_enable_title_display(void);
int ngb_title_display_enabled(void);
void ngb_direct_close(void);
void ngb_direct_park_prologue(void);
void ngb_direct_wait_texture(uint32_t header);
uint8_t *ngb_direct_lock_prologue_texture(uint32_t header, unsigned width, unsigned height, int *pitch);
void ngb_prologue_simple_state(uint32_t method, uint32_t value);
#define NGB_DIRECT_KICKOFF_KIB 256u
void ngb_direct_finish_put(void);
void ngb_direct_render_core(void);
void ngb_direct_render_event(int renderer, int active);
void ngb_direct_check_render_error(void);
void ngb_direct_check_stop(const char*, uint32_t);
uint64_t ngb_elapsed_ns(void);
/* Read only on the cooperative guest thread; GPU/render counters stay continuous. */
extern int ngb_direct_detail_frame;
void ngb_direct_timing_flip(unsigned completed);
void ngb_direct_draw_time(uint64_t sync_ns, uint64_t record_ns);
uint64_t ngb_direct_fifo_batched_words(void);
void ngb_direct_draw_pairs(unsigned same_state, unsigned lists, unsigned merged, unsigned index_hits);
int ngb_direct_try_indexed(uint64_t *reference_start);
void ngb_direct_index_reference_done(uint64_t start);
void ngb_direct_index_reset(void);
void ngb_direct_mesh_scope(int enter);
void ngb_direct_index_close(void);
void ngb_direct_index_report(void);
void ngb_direct_index_stats(uint64_t* draws, uint64_t* indices);
void ngb_direct_present_time(uint64_t ns, unsigned draws, unsigned drawn, int published);
void ngb_direct_gpu_time(uint64_t ns, int valid);
void ngb_direct_queue_time(uint64_t ns);
void ngb_direct_fence_time(uint64_t ns);
void ngb_direct_publish_time(uint64_t ns);
void ngb_direct_geometry_bytes(uint64_t requested, uint64_t reused);
void ngb_direct_binding_counts(uint64_t requested, uint64_t written);
void ngb_direct_stats(void);
#ifdef __SWITCH__
unsigned ngb_direct_sample_scope(void);
void ngb_profile_next_frame(unsigned frame, unsigned draws);
void ngb_direct_visit_worker(void (*visit)(void*));
void ngb_direct_forget_worker(void);
#endif
void ngb_direct_reset_stats(void);
void ngb_kernel_log(const char *message);
#ifdef __cplusplus
}
#endif
