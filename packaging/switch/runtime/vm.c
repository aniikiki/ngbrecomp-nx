/* Xbox Nt* guest layouts follow kernel_bridge.c. Keep reserve/commit state
 * here: a reserved page is not accessible, and decommit clears its contents.
 * This bounded arena doesn't yet model the full 4 GiB virtual address space. */
#ifdef NGB_DIRECT3D
#include "direct/output.h"
#endif
#include "vm.h"
#include "guest_memory.h"
#include <string.h>

#define PAGE 4096u
#define PAGES ((NGB_VM_END - NGB_VM_BEGIN) / PAGE)
#define INVALID 0xc000000du
#define CONFLICT 0xc0000018u
#define NO_MEMORY 0xc0000017u
#define NOT_ALLOCATED 0xc00000a0u
#define RESERVE 0x2000u
#define COMMIT 0x1000u
static struct { uint32_t owner; unsigned char committed; uint16_t pins; } pages[PAGES];
uint16_t ngb_fast_page_bytes[1u << 20];
unsigned char *ngb_fast_ram;
static unsigned char *memory;
unsigned char *ngb_direct_pages[NGB_RAM_BYTES / PAGE];
unsigned char **ngb_guest_banks[64];

void ngb_vm_init(unsigned char *guest_ram)
{
    memory = ngb_fast_ram = guest_ram;
    memset(ngb_fast_page_bytes, 0, sizeof(ngb_fast_page_bytes));
    memset(ngb_guest_banks, 0, sizeof(ngb_guest_banks));
    ngb_guest_banks[0] = ngb_direct_pages;
    memset(ngb_direct_pages, 0, sizeof(ngb_direct_pages));
    if (memory) {
        for (unsigned addr = PAGE; addr < NGB_RAM_BYTES; addr += PAGE) {
            if ((addr < NGB_VM_BEGIN || addr >= NGB_VM_END) && addr != (NGB_TICK_COUNT & ~(PAGE-1))) {
                ngb_direct_pages[addr / PAGE] = memory + addr;
                ngb_fast_page_bytes[addr / PAGE] = PAGE;
            }
        }
    }
    memset(pages, 0, sizeof(pages));
}

static int range(uint32_t base, uint32_t size, unsigned *first, unsigned *count)
{
    uint64_t end = ((uint64_t)base + size + PAGE - 1) & ~(uint64_t)(PAGE - 1);
    uint32_t begin = base & ~(PAGE - 1);
    if (!size || begin < NGB_VM_BEGIN || end > NGB_VM_END) return 0;
    *first = (begin - NGB_VM_BEGIN) / PAGE;
    *count = (unsigned)((end - begin) / PAGE);
    return 1;
}

uint32_t ngb_vm_allocate(uint32_t *base, uint32_t *size, uint32_t zero_bits,
                         uint32_t flags, uint32_t protection)
{
    if (!memory || !base || !size || !*size || zero_bits ||
        !(flags & (RESERVE | COMMIT)) || (flags & ~(RESERVE | COMMIT))) return INVALID;
    /* Only PAGE_READWRITE has access semantics in the current adapter. */
    if (protection != 4) return 0xc0000045u;
    unsigned first = 0, count;
    uint32_t address = *base;
    int fresh = !address || (flags & RESERVE);
    if (!address) {
        uint64_t rounded = ((uint64_t)*size + PAGE - 1) & ~(uint64_t)(PAGE - 1);
        if (rounded > NGB_VM_END - NGB_VM_BEGIN) return NO_MEMORY;
        count = (unsigned)(rounded / PAGE);
        unsigned run = 0;
        for (unsigned i = 0; i < PAGES; ++i) {
            run = pages[i].owner ? 0 : run + 1;
            if (run == count) { first = i + 1 - count; break; }
        }
        if (run < count) return NO_MEMORY;
    } else if (!range(address, *size, &first, &count)) return CONFLICT;
    address = NGB_VM_BEGIN + first * PAGE;
    uint32_t owner = fresh ? address : pages[first].owner;
    if (!owner) return CONFLICT;
    for (unsigned i = first; i < first + count; ++i)
        if (fresh ? pages[i].owner != 0 : pages[i].owner != owner) return CONFLICT;
    for (unsigned i = first; i < first + count; ++i) {
        pages[i].owner = owner;
        if ((flags & COMMIT) && !pages[i].committed) {
            memset(memory + NGB_VM_BEGIN + i * PAGE, 0, PAGE);
            pages[i].committed = 1;
            ngb_fast_page_bytes[NGB_VM_BEGIN/PAGE + i] = PAGE;
            ngb_direct_pages[NGB_VM_BEGIN/PAGE + i] = memory + NGB_VM_BEGIN + i*PAGE;
        }
    }
    *base = address;
    *size = count * PAGE;
    return 0;
}

uint32_t ngb_vm_free(uint32_t *base, uint32_t *size, uint32_t flags)
{
    if (!memory || !base || !size || (flags != 0x8000 && flags != 0x4000)) return INVALID;
    if (*base < NGB_VM_BEGIN || *base >= NGB_VM_END) return NOT_ALLOCATED;
    unsigned first = (*base - NGB_VM_BEGIN) / PAGE, count;
    uint32_t owner = pages[first].owner;
    if (!owner) return NOT_ALLOCATED;
    if (flags == 0x8000 || !*size) {
        if (*base != owner || *size) return INVALID;
        count = 0;
        while (first + count < PAGES && pages[first + count].owner == owner) ++count;
    } else if (!range(*base, *size, &first, &count)) return INVALID;
    for (unsigned i = first; i < first + count; ++i)
        if (pages[i].owner != owner || pages[i].pins) return CONFLICT;
#ifdef NGB_DIRECT3D
    ngb_direct_finish_put();
#endif
    for (unsigned i = first; i < first + count; ++i) {
        if (pages[i].committed) memset(memory + NGB_VM_BEGIN + i * PAGE, 0, PAGE);
        pages[i].committed = 0;
        ngb_fast_page_bytes[NGB_VM_BEGIN/PAGE + i] = 0;
        ngb_direct_pages[NGB_VM_BEGIN/PAGE + i] = NULL;
        if (flags == 0x8000) pages[i].owner = 0;
    }
    *base = NGB_VM_BEGIN + first * PAGE;
    *size = count * PAGE;
    return 0;
}

uint32_t ngb_vm_query(uint32_t address, uint32_t info[7])
{
    if (!info || address < NGB_VM_BEGIN || address >= NGB_VM_END) return INVALID;
    unsigned first = (address - NGB_VM_BEGIN) / PAGE, end = first + 1;
    while (end < PAGES && pages[end].owner == pages[first].owner &&
           pages[end].committed == pages[first].committed) ++end;
    info[0] = NGB_VM_BEGIN + first * PAGE;
    info[1] = pages[first].owner;
    info[2] = pages[first].owner ? 4 : 0;
    info[3] = (end - first) * PAGE;
    info[4] = pages[first].owner ? (pages[first].committed ? COMMIT : RESERVE) : 0x10000;
    info[5] = pages[first].committed ? 4 : 0;
    info[6] = pages[first].owner ? 0x20000 : 0;
    return 0;
}

int ngb_vm_access(uint32_t address, size_t bytes)
{
    unsigned first, count;
    if (!memory || bytes > UINT32_MAX || !range(address, (uint32_t)bytes, &first, &count)) return 0;
    for (unsigned i = first; i < first + count; ++i)
        if (!pages[i].committed) return 0;
    return 1;
}

int ngb_vm_pin(uint32_t address, uint32_t bytes, int unlock)
{
    unsigned first,count;
    if (!ngb_vm_access(address,bytes) || !range(address,bytes,&first,&count)) return 0;
    for (unsigned i=first;i<first+count;i++)
        if (unlock ? !pages[i].pins : pages[i].pins==UINT16_MAX) return 0;
    for (unsigned i=first;i<first+count;i++) pages[i].pins+=unlock ? -1 : 1;
    return 1;
}
