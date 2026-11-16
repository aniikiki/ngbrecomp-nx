#pragma once
#include <stdint.h>
void ngb_timers_reset(void);
int ngb_timer_initialize(uint32_t address);
int ngb_timer_arm(uint32_t address, uint64_t now, uint64_t delay,
                  uint64_t period, uint32_t dpc);
int ngb_timer_cancel(uint32_t address);
void ngb_timers_poll(uint64_t now, void (*fire)(uint32_t address, uint32_t dpc, int periodic));
