#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void ngb_combat_wait(int active);
uint64_t ngb_combat_wait_us(void);
extern int ngb_combat_enabled; /* immutable once workers start */
int ngb_combat_active(void);
uint64_t ngb_combat_cpu_us(void); /* zero if thread clock unavailable */
void ngb_combat_guest(unsigned frame,unsigned id,unsigned mode,unsigned difficulty,unsigned hp,unsigned maxhp,
                      unsigned displayed,uint64_t io_ops,uint64_t io_bytes,uint64_t io_us);
void ngb_combat_row(int kind,const uint64_t *values,unsigned count);
#ifdef __cplusplus
}
#endif
