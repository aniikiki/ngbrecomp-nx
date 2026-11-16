#pragma once
#include <stdint.h>

static inline int ngb_nv2a_contains(uint32_t va)
{
    return va - 0xfd000000u < 0x01000000u;
}

uint32_t ngb_nv2a_field(void);
uint32_t ngb_nv2a_irq_pending(void);
void ngb_nv2a_reset(void);
void ngb_nv2a_write8(uint32_t va, uint8_t value);
uint8_t ngb_nv2a_read8(uint32_t va);
uint32_t ngb_nv2a_read32(uint32_t va);
void ngb_nv2a_write32(uint32_t va, uint32_t value);
