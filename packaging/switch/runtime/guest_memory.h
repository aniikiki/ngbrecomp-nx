#pragma once
#include "runtime.h"
#include "vm.h"

#ifdef __SWITCH__
#pragma GCC visibility push(hidden)
#endif

extern uint64_t ngb_guest_polls;
extern unsigned ngb_pending_dpcs, ngb_poll_mask;
void ngb_poll_due(uint64_t ticket);

static inline void ngb_guest_block_poll(void)
{
    uint64_t ticket = ++ngb_guest_polls;
    if (!(ticket & ngb_poll_mask) || ngb_pending_dpcs)
        ngb_poll_due(ticket);
}

#define NGB_RAM_BYTES (64u * 1024u * 1024u)
#define NGB_TICK_COUNT 0x7054u
extern unsigned char *ngb_direct_pages[NGB_RAM_BYTES / 4096];

/* Each non-null bank describes 64 MiB of ordinary RAM in 4 KiB pages.
 * Device registers, protected pages, the tick counter and cross-page accesses
 * still go through ngb_guest_pointer. */
extern unsigned char **ngb_guest_banks[64];
static inline void *ngb_ram_span(uint32_t address, size_t bytes)
{
    unsigned offset = address & 4095;
    unsigned char **bank = ngb_guest_banks[address >> 26];
    if (bank && bytes <= 4096 - offset) {
        unsigned char *page = bank[(address >> 12) & 0x3fff];
        if (page) return page + offset;
    }
    return NULL;
}

/* All ordinary low pages and active physical aliases share one RAM allocation.
 * A single indexed load covers the entire guest address space, including MMIO
 * holes. Each mapped entry admits accesses ending within its 4 KiB page. */
extern uint16_t ngb_fast_page_bytes[1u << 20];
extern unsigned char *ngb_fast_ram;
uintptr_t ngb_guest_scalar_fallback(uint32_t address, size_t bytes);
/* Image code, globals and static buffers occupy ordinary RAM between the
 * tick-counter page and the VM arena. For literal addresses the compiler
 * can resolve the entire bounds check, even across a page boundary. */
static inline __attribute__((always_inline)) int ngb_static_image_span(uint32_t address, size_t bytes)
{
    return __builtin_constant_p(address) && __builtin_constant_p(bytes) &&
           address >= (NGB_TICK_COUNT | 4095u) + 1u && address < NGB_VM_BEGIN &&
           bytes <= NGB_VM_BEGIN - address;
}

static inline __attribute__((always_inline)) uintptr_t ngb_guest_scalar(uint32_t address, size_t bytes)
{
    if (ngb_static_image_span(address, bytes) && ngb_fast_ram)
        return (uintptr_t)(ngb_fast_ram + address);
    if (__builtin_expect((address & 4095u) + bytes <= ngb_fast_page_bytes[address >> 12], 1))
        return (uintptr_t)ngb_fast_ram + (address & 0x7fffffffu);
    return ngb_guest_scalar_fallback(address, bytes);
}

static inline uintptr_t ngb_guest_scalar_paged(uint32_t address, size_t bytes)
{
    void *p = ngb_ram_span(address, bytes);
    return p ? (uintptr_t)p : ngb_guest_pointer(address, bytes);
}

void *ngb_guest_high_vector(uint32_t address);
static inline void *ngb_guest_vector_page(uint32_t address)
{
    if (__builtin_expect((address & 4095u) + 16u <= ngb_fast_page_bytes[address >> 12], 1))
        return ngb_fast_ram + (address & 0x7fffffffu);
    if ((address & 4095) > 4096 - 16) return NULL;
    void *p = ngb_ram_span(address, 16);
    if (p || address < NGB_RAM_BYTES) return p;
    return ngb_guest_high_vector(address);
}

void ngb_vector_read_slow(uint32_t address, uint32_t lanes[4]);
void ngb_vector_write_slow(uint32_t address, const uint32_t lanes[4]);

#ifdef __SWITCH__
#pragma GCC visibility pop
#endif
