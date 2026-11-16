#pragma once
#include <stdint.h>
#include "audio_boot.h"

void ngb_ohci_pad_sample(uint16_t buttons, int16_t lx, int16_t ly, int16_t rx, int16_t ry);
void ngb_warning_file_read(const char *name, int64_t offset);
void ngb_pad_flip(void);
void ngb_menu_draw(uint32_t cursor);
uint64_t ngb_warning_start_time(void);
void ngb_ohci_pad_present(int present);
uint32_t ngb_ohci_irq_pending(void);
void ngb_ohci_reset(void);
uint32_t ngb_bus_read32(uint32_t va);
void ngb_bus_write32(uint32_t va, uint32_t value);

unsigned ngb_start_press_count(void);

unsigned ngb_movie_skip_edges(void);
