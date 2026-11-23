#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#ifndef NGB_DIAG
#ifdef __SWITCH__
#include "player_diagnostics.h"
#else
#define NGB_DIAG 1
#endif
#endif

/* Bootstrap statuses are intentionally distinct from a playable game. */
enum { NGB_BOOT_RETURNED, NGB_BOOT_UNSUPPORTED, NGB_BOOT_ERROR, NGB_BOOT_CANCELLED };
int ngb_boot(const char *xbe_path, FILE *log);
void ngb_request_stop(void);
const char *ngb_boot_reason(void);
uintptr_t ngb_guest_pointer(uint32_t va, size_t bytes);
void ngb_device_return(uint32_t result);
void ngb_checkpoint(uint32_t va);
void ngb_poll(void);
uint64_t ngb_elapsed_ns(void);
void ngb_graphics_wait_until(uint64_t nanoseconds);
void ngb_kernel_log(const char *message);
void ngb_kernel_logf(const char *format, ...) __attribute__((format(printf, 1, 2)));
/* Avoid preparing arguments or formatting a message for a disabled boot log. */
#define NGB_BOOT_LOGF(...) do { if (NGB_DIAG) ngb_kernel_logf(__VA_ARGS__); } while (0)
void ngb_scene_log_begin(void);
void ngb_scene_log_end(void);
uint32_t ngb_query_setting(uint32_t index, uint32_t type, uint32_t value,
                           uint32_t length, uint32_t result);
_Noreturn void ngb_stop(const char *reason, uint32_t detail);

void *ngb_dma_pointer(uint32_t address, size_t size);

void ngb_select_movie(uint32_t path_address);
uint32_t ngb_movie_status(uint32_t guest_status);
int ngb_stop_requested(void);
const uint32_t *ngb_prologue_pixels(void);
int ngb_movie_owns_input(void);
void ngb_movie_displayed(void);
