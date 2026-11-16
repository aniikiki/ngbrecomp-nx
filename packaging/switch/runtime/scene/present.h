#pragma once
#include "scene.h"
enum NgbPresent ngb_present_surface(NV2AState *d, uint32_t address, unsigned pitch, void *pixels);
void ngb_present_stats(void);
void ngb_present_close(void);
