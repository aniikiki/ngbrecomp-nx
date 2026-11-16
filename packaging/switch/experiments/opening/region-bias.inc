/* A 64 KiB region PLUS its successor page must be ordinary linear RAM.
 * Only use the low guest RAM alias.
 * Incomplete regions still use the original one-page path. Store integers:
 * subtracting a guest address from a C pointer isn't valid pointer arithmetic. */
uintptr_t ngb_region_bias[65536];
static void refresh_region(unsigned region)
{
    unsigned start=region<<4;
    uintptr_t bias=0;
    /* Contiguous high aliases can straddle separately owned allocations.
     * VM arena boundaries also have distinct cross-span semantics. */
    if (region<32767 && (region+1u)*65536u!=NGB_VM_BEGIN &&
        (region+1u)*65536u!=NGB_VM_END && ngb_fast_ram) {
        unsigned i=0;
        for (;i<17;++i) if (ngb_fast_page_bytes[start+i]!=4096u) break;
        if (i==17) bias=(uintptr_t)ngb_fast_ram;
    }
    ngb_region_bias[region]=bias;
}
void ngb_region_changed(unsigned page)
{
    refresh_region(page>>4);
    if (!(page&15u) && page) refresh_region((page>>4)-1);
}
