#pragma once
#include <stdint.h>
void ngb_devices_reset(void);
unsigned ngb_files_arg_count(uint32_t ordinal);
uint32_t ngb_files_dispatch(uint32_t ordinal, const uint32_t *args);

int ngb_io_event(uint32_t handle, int signalled);
