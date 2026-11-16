#pragma once
#include <stdint.h>

/* Before the first draw, these methods affect only guest-visible register
 * state, constants, DMA bindings, or a word in guest semaphore memory. */
void ngb_pgraph_reset(void);
void ngb_pgraph_method(uint32_t *regs, uint32_t cls, uint32_t method, uint32_t parameter);
uint32_t *ngb_pgraph_constant_word(uint32_t rdi_word);
