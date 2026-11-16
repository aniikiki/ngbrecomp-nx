#pragma once
#include <stddef.h>
#include <stdint.h>

#define NGB_PRAMIN_BASE 0xfd700000u
#define NGB_INSTANCE_PADDING 0x10000u

extern uint8_t ngb_target_pages[], ngb_vertex_dirty[], ngb_texture_dirty[];
extern uint8_t *ngb_contiguous_pages[];
uint32_t ngb_instance_claim(uint32_t bytes);
void *ngb_instance_aperture(uint32_t va, size_t bytes);
uint32_t ngb_contiguous_allocate(uint32_t bytes, uint32_t low, uint32_t high, uint32_t alignment, uint32_t protection);
int ngb_contiguous_pin(uint32_t va, uint32_t bytes, int unlock);
int ngb_contiguous_free(uint32_t va);
int ngb_contiguous_in_pool(uint32_t va);
int ngb_contiguous_query(uint32_t va, uint32_t info[7], uint32_t *allocation_size);
void *ngb_contiguous_pointer_raw(uint32_t va, size_t bytes);
void *ngb_contiguous_pointer(uint32_t va, size_t bytes);
uint32_t ngb_contiguous_physical(uint32_t va);
void ngb_contiguous_reset(void);
void ngb_contiguous_set_ram(unsigned char *base);
void ngb_contiguous_map_guest_banks(int enable);

int ngb_contiguous_protect(uint32_t va,uint32_t bytes,uint32_t protection);
