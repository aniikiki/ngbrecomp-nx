#pragma once
#include <stdint.h>
uint32_t ngb_status_to_error(uint32_t status);
void ngb_time_to_fields(uint32_t time_address, uint32_t fields_address);
uint32_t ngb_equal_string(uint32_t first, uint32_t second, uint32_t nocase);
void ngb_xc_hmac(const uint32_t args[7]);
void ngb_xc_sha(unsigned ordinal,uint32_t ctx,uint32_t data,uint32_t bytes);
void ngb_video_init(void);
uint32_t ngb_av_pack(void);

#ifdef __SWITCH__
int ngb_mmio_trace_enabled(void);
#else
static inline int ngb_mmio_trace_enabled(void) { return 1; }
#endif
