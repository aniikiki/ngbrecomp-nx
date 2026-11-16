#include "vm.h"
#include "guest_memory.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
int main(void)
{
    unsigned char *ram = calloc(1, 64 * 1024 * 1024);
    CHECK(ram);
    ngb_vm_init(ram);
    CHECK(!ngb_direct_pages[0] && !ngb_direct_pages[NGB_TICK_COUNT >> 12]);
    uint32_t base = 0, size = 8193, info[7];
    CHECK(ngb_vm_allocate(&base, &size, 0, 0x2000, 4) == 0);
    CHECK(base == NGB_VM_BEGIN && size == 12288);
    CHECK(!ngb_vm_access(base, 1) && !ngb_direct_pages[base >> 12]);
    CHECK(ngb_vm_query(base, info) == 0 && info[4] == 0x2000 && info[3] == size);
    uint32_t commit = base + 4096, length = 4096;
    CHECK(ngb_vm_allocate(&commit, &length, 0, 0x1000, 4) == 0);
    CHECK(ngb_vm_access(commit, 4096) && !ngb_vm_access(commit, 4097));
    CHECK(ngb_fast_page_bytes[commit >> 12] == 4096 && !ngb_fast_page_bytes[base >> 12]);
    CHECK(!ngb_fast_page_bytes[0] && !ngb_fast_page_bytes[NGB_TICK_COUNT >> 12]);
    CHECK(ngb_direct_pages[commit >> 12] == ram + commit);
    CHECK(ngb_vm_query(commit, info) == 0 && info[1] == base && info[4] == 0x1000);
    CHECK(ngb_vm_pin(commit+1, 4095, 0));
    CHECK(!ngb_vm_pin(commit+1, 4096, 0));
    CHECK(ngb_vm_free(&commit, &length, 0x4000) != 0);
    CHECK(ngb_vm_pin(commit+1, 4095, 1));
    CHECK(!ngb_vm_pin(commit, 1, 1));
    ram[commit] = 123;
    CHECK(ngb_vm_allocate(&commit, &length, 0, 0x1000, 4) == 0 && ram[commit] == 123);
    CHECK(ngb_vm_free(&commit, &length, 0x4000) == 0 && !ngb_vm_access(commit, 1));
    CHECK(!ngb_direct_pages[commit >> 12] && !ngb_fast_page_bytes[commit >> 12]);
    CHECK(ngb_vm_allocate(&commit, &length, 0, 0x1000, 4) == 0 && ram[commit] == 0);
    CHECK(ngb_direct_pages[commit >> 12] == ram + commit);
    uint32_t overlap = base, overlap_size = 4096;
    CHECK(ngb_vm_allocate(&overlap, &overlap_size, 0, 0x3000, 4) == 0xc0000018u);
    uint32_t second = 0, second_size = 4096;
    CHECK(ngb_vm_allocate(&second, &second_size, 0, 0x3000, 4) == 0);
    CHECK(second == base + 12288);
    commit = base + 8192; length = 8192;
    CHECK(ngb_vm_allocate(&commit, &length, 0, 0x1000, 4) == 0xc0000018u);
    CHECK(!ngb_vm_access(commit, 1)); /* failed range commit must be atomic */
    uint32_t release = base, zero = 0;
    CHECK(ngb_vm_free(&release, &zero, 0x8000) == 0 && zero == size);
    CHECK(!ngb_vm_access(base, 1) && ngb_vm_access(second, 4096));
    CHECK(ngb_vm_query(base, info) == 0 && info[4] == 0x10000);
    uint32_t reused = 0, reused_size = 4096;
    CHECK(ngb_vm_allocate(&reused, &reused_size, 0, 0x3000, 4) == 0 && reused == base);
    uint32_t huge = 0, huge_size = UINT32_MAX;
    CHECK(ngb_vm_allocate(&huge, &huge_size, 0, 0x2000, 4) == 0xc0000017u && huge == 0);
    uint32_t edge = NGB_VM_END - 4096, edge_size = 4097;
    CHECK(ngb_vm_allocate(&edge, &edge_size, 0, 0x3000, 4) != 0);
    CHECK(!ngb_vm_access(NGB_VM_END - 1, 2));
    CHECK(ngb_vm_allocate(&huge, &reused_size, 0, 0x3000, 2) == 0xc0000045u);
    ngb_vm_init(NULL);
    CHECK(!ngb_direct_pages[second >> 12]);
    free(ram);
    puts("Guest VM: reserve/commit/query/decommit/release/bounds passed");
    return 0;
}
