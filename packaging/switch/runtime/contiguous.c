#ifdef NGB_DIRECT3D
#include "direct/output.h"
#endif
#include "contiguous.h"
#include "guest_memory.h"
#include "menu_gpu.h"
#include "scene.h"
#include "kernel/kernel.h"
#include <stdlib.h>
#include <string.h>

#define PAGE_BYTES 4096u

/* During a boot, the CPU and PGRAPH share one physical RAM window. */
static unsigned char *physical_ram;
void ngb_contiguous_set_ram(unsigned char *base) { physical_ram = base; }
struct block {
    struct block *next;
    uint32_t physical, length, protection;
    unsigned char *data;
    struct { uint16_t pins, protection; } pages[];
};
static struct block *blocks;
uint8_t *ngb_contiguous_pages[XBOX_CONTIG_SIZE/PAGE_BYTES];
static struct block *physical_pages[XBOX_CONTIG_SIZE/PAGE_BYTES];

static void refresh_fast_pages(uint32_t physical, uint32_t length)
{
    unsigned begin = physical / PAGE_BYTES;
    unsigned end = begin + length / PAGE_BYTES;
    unsigned alias = XBOX_CONTIG_BASE / PAGE_BYTES;
    for (unsigned i = begin; i < end; ++i) {
        bool mapped = physical_ram && physical_ram == ngb_fast_ram &&
                      ngb_guest_banks[(alias + i) >> 14] &&
                      ngb_contiguous_pages[i] == physical_ram + (size_t)i * PAGE_BYTES;
        ngb_fast_page_bytes[alias + i] = mapped ? PAGE_BYTES : 0;
    }
}

/* Only the Direct3D renderer uses these aliases: it reads vertex and texture
 * bytes from RAM. The GL renderer needs its CPU-access notifications. */
void ngb_contiguous_map_guest_banks(int enable)
{
    for (unsigned offset = 0; offset < XBOX_CONTIG_SIZE; offset += NGB_RAM_BYTES) {
        unsigned bank = (XBOX_CONTIG_BASE + offset) >> 26;
        ngb_guest_banks[bank] = enable ? &ngb_contiguous_pages[offset / PAGE_BYTES] : NULL;
    }
    refresh_fast_pages(0, XBOX_CONTIG_SIZE);
}

/* The driver subtracts its claim size from the returned exclusive top.
 * Keep the top padding and instance reserve out of ordinary allocations. */
#define INSTANCE_TOP (XBOX_CONTIG_SIZE - NGB_INSTANCE_PADDING)
#define INSTANCE_FLOOR (INSTANCE_TOP - XBOX_GPU_INSTANCE_DEFAULT)
static _Alignas(64) unsigned char instance_ram[XBOX_GPU_INSTANCE_DEFAULT];
static uint32_t instance_bytes;
static int instance_claimed;

uint32_t ngb_instance_claim(uint32_t bytes)
{
    if (bytes == UINT32_MAX)
        bytes = instance_claimed ? instance_bytes : XBOX_GPU_INSTANCE_DEFAULT;
    if (bytes > XBOX_GPU_INSTANCE_DEFAULT) return 0;
    uint32_t rounded = (bytes + PAGE_BYTES - 1) & ~(PAGE_BYTES - 1);
    if (rounded > instance_bytes) {
        for (struct block *block = blocks; block; block = block->next)
            if (block->physical + block->length > INSTANCE_TOP - rounded) return 0;
        memset(instance_ram + sizeof(instance_ram) - rounded, 0, rounded - instance_bytes);
    }
    instance_bytes = rounded;
    instance_claimed = 1;
    return XBOX_CONTIG_BASE + INSTANCE_TOP;
}

void *ngb_instance_aperture(uint32_t va, size_t bytes)
{
    uint32_t offset = va - (NGB_PRAMIN_BASE + NGB_INSTANCE_PADDING);
    if (offset >= instance_bytes || bytes > instance_bytes - offset) return NULL;
    /* NV20-family RAMIN addresses descend through physical RAM in 64-byte
     * units. Bytes inside a unit retain their little-endian order. */
    if (bytes > 64 - (offset & 63)) return NULL;
    size_t index = sizeof(instance_ram) - 64 - (offset & ~63u) + (offset & 63);
    return instance_ram + index;
}

uint32_t ngb_contiguous_allocate(uint32_t bytes, uint32_t low, uint32_t high, uint32_t alignment, uint32_t protection)
{
    if (protection != 4 && protection != 0x404) return 0;
    if (!bytes || (alignment && (alignment & (alignment - 1)))) return 0;
    if (alignment < PAGE_BYTES) alignment = PAGE_BYTES;
    uint64_t length = ((uint64_t)bytes + PAGE_BYTES - 1) & ~(uint64_t)(PAGE_BYTES - 1);
    uint64_t limit = (uint64_t)high + 1;
    uint32_t ceiling = instance_claimed ? INSTANCE_TOP - instance_bytes : INSTANCE_FLOOR;
    if (limit > ceiling) limit = ceiling;
    uint64_t start = low > XBOX_CONTIG_ALLOC_BASE ? low : XBOX_CONTIG_ALLOC_BASE;
    struct block **slot = &blocks;
    for (;;) {
        start = (start + alignment - 1) & ~(uint64_t)(alignment - 1);
        if (start + length > limit) return 0;
        struct block *next = *slot;
        if (!next || start + length <= next->physical) break;
        uint64_t end = next->physical + next->length;
        if (start < end) start = end;
        slot = &next->next;
    }
    struct block *block = calloc(1, sizeof(*block) + length / PAGE_BYTES * sizeof(block->pages[0]));
    if (!block) return 0;
    if (physical_ram && ngb_scene_active) ngb_scene_cpu_access((uint32_t)start, (size_t)length);
    block->data = physical_ram ? memset(physical_ram + start, 0, (size_t)length) : calloc(1, (size_t)length);
    if (!block->data) { free(block); return 0; }
    block->protection = protection;
    for (size_t i = 0; i < length / PAGE_BYTES; ++i)
        block->pages[i].protection = protection;
    block->physical = (uint32_t)start;
    block->length = (uint32_t)length;
    block->next = *slot;
    *slot = block;
    for (size_t page = 0; page < length / PAGE_BYTES; ++page) {
        physical_pages[start / PAGE_BYTES + page] = block;
        ngb_contiguous_pages[start / PAGE_BYTES + page] = block->data + page * PAGE_BYTES;
    }
    refresh_fast_pages(block->physical, block->length);
    return XBOX_CONTIG_BASE + block->physical;
}

int ngb_contiguous_in_pool(uint32_t va)
{
    uint32_t offset = va - XBOX_CONTIG_BASE;
    return offset >= XBOX_CONTIG_ALLOC_BASE && offset < XBOX_CONTIG_SIZE;
}

static struct block *find_block(uint32_t va)
{
    uint32_t physical = va - XBOX_CONTIG_BASE;
    return physical < XBOX_CONTIG_SIZE ? physical_pages[physical/PAGE_BYTES] : NULL;
}

void *ngb_contiguous_pointer(uint32_t va, size_t bytes)
{
    void *ptr=ngb_contiguous_pointer_raw(va,bytes);
    if (ptr && ngb_scene_active) ngb_scene_cpu_access(va-XBOX_CONTIG_BASE, bytes);
    if (ptr) ngb_menu_gpu_sync(ptr,bytes);
    return ptr;
}

void *ngb_contiguous_pointer_raw(uint32_t va, size_t bytes)
{
    uint32_t physical = va - XBOX_CONTIG_BASE;
    if (physical >= INSTANCE_TOP - instance_bytes && physical < INSTANCE_TOP)
        return bytes <= INSTANCE_TOP - physical ? instance_ram + (physical - INSTANCE_FLOOR) : NULL;
    struct block *block = find_block(va);
    if (!block) return NULL;
    uint32_t offset = va - XBOX_CONTIG_BASE - block->physical;
    return bytes <= block->length - offset ? block->data + offset : NULL;
}

int ngb_contiguous_protect(uint32_t va, uint32_t bytes, uint32_t protection)
{
    struct block *block = find_block(va);
    if (!block || !bytes || (protection != 4 && protection != 0x404 && protection != 0x204))
        return 0;
    uint32_t offset = va - XBOX_CONTIG_BASE - block->physical;
    if (bytes > block->length - offset) return 0;
    unsigned last = (offset + bytes - 1) / PAGE_BYTES;
    for (unsigned page = offset / PAGE_BYTES; page <= last; ++page)
        block->pages[page].protection = protection;
    return 1;
}

/* Report both the allocation and the run of equal-protection pages from VA. */
int ngb_contiguous_query(uint32_t va, uint32_t info[7], uint32_t *allocation_size)
{
    uint32_t physical = va - XBOX_CONTIG_BASE;
    uint32_t start = va & ~(PAGE_BYTES - 1);
    int instance = physical >= INSTANCE_TOP - instance_bytes && physical < INSTANCE_TOP;
    struct block *block = instance ? NULL : find_block(va);
    if (!instance && !block) return 0;
    info[0] = start;
    info[4] = 0x1000;
    info[6] = 0x20000;
    if (instance) {
        info[1] = XBOX_CONTIG_BASE + INSTANCE_TOP - instance_bytes;
        info[2] = info[5] = 4;
        info[3] = instance_bytes - (start - info[1]);
        *allocation_size = instance_bytes;
        return 1;
    }
    info[1] = XBOX_CONTIG_BASE + block->physical;
    info[2] = block->protection;
    unsigned first = (start - info[1]) / PAGE_BYTES;
    info[5] = block->pages[first].protection;
    unsigned end = first + 1;
    while (end < block->length / PAGE_BYTES && block->pages[end].protection == info[5]) ++end;
    info[3] = (end - first) * PAGE_BYTES;
    *allocation_size = block->length;
    return 1;
}

int ngb_contiguous_pin(uint32_t va, uint32_t bytes, int unlock)
{
    struct block *block = find_block(va);
    if (!block || !bytes) return 0;
    uint32_t offset = va - XBOX_CONTIG_BASE - block->physical;
    if (bytes > block->length - offset) return 0;
    uint32_t first = offset / PAGE_BYTES, last = (offset + bytes - 1) / PAGE_BYTES;
    for (uint32_t i = first; i <= last; ++i)
        if (unlock ? !block->pages[i].pins : block->pages[i].pins == UINT16_MAX) return 0;
    for (uint32_t i = first; i <= last; ++i)
        block->pages[i].pins += unlock ? -1 : 1;
    return 1;
}

int ngb_contiguous_free(uint32_t va)
{
    struct block **slot = &blocks;
    while (*slot && XBOX_CONTIG_BASE + (*slot)->physical != va) slot = &(*slot)->next;
    if (!*slot) return 0;
    struct block *block = *slot;
    for (size_t i = 0; i < block->length / PAGE_BYTES; ++i)
        if (block->pages[i].pins) return 0;
#ifdef NGB_DIRECT3D
    ngb_direct_finish_put();
#endif
    *slot = block->next;
    memset(ngb_contiguous_pages + block->physical / PAGE_BYTES, 0, block->length / PAGE_BYTES * sizeof(*ngb_contiguous_pages));
    memset(physical_pages+block->physical/PAGE_BYTES,0,(block->length/PAGE_BYTES)*sizeof(*physical_pages));
    refresh_fast_pages(block->physical, block->length);
    if (!physical_ram) free(block->data);
    free(block);
    return 1;
}

uint32_t ngb_contiguous_physical(uint32_t va)
{
    uint32_t offset = va - XBOX_CONTIG_BASE;
    return offset < XBOX_CONTIG_SIZE ? offset : va;
}

void ngb_contiguous_reset(void)
{
    ngb_contiguous_map_guest_banks(0);
    memset(ngb_contiguous_pages, 0, sizeof(ngb_contiguous_pages));
    memset(physical_pages,0,sizeof(physical_pages));
    instance_bytes = 0;
    instance_claimed = 0;
    while (blocks) {
        struct block *next = blocks->next;
        if (!physical_ram) free(blocks->data);
        free(blocks);
        blocks = next;
    }
    physical_ram = NULL;
}
