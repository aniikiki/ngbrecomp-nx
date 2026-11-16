#pragma once
#include <stdint.h>
#include <stddef.h>
void ngb_audio_reset(void);
uint32_t ngb_apu_read(uint32_t va);
void ngb_apu_write(uint32_t va, uint32_t value);
uint32_t ngb_ac97_read(uint32_t va, unsigned size);
void ngb_ac97_write(uint32_t va, unsigned size, uint32_t value);
uint32_t ngb_audio_irq(unsigned line);

void ngb_audio_poll(void);

void *ngb_dsp_memory(uint32_t address, size_t bytes);
