#pragma once
#include <stdint.h>

#if defined(__SWITCH__) && defined(NGB_DIRECT3D)
void ngb_profile_work_counts(uint64_t *entries, uint64_t *polls, uint64_t *switches, uint64_t *skips);
/* Called only with the guest thread paused. */
uintptr_t ngb_profile_fiber_stack_end(uintptr_t sp);
unsigned ngb_profile_worker_id(void);
#endif
