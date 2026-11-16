/* The Xbox device has already allocated this light. A redundant enable
 * or disable still marks it dirty. Preserve that write, the guest stack
 * spills, clobbered registers, original HLE hooks and entry checkpoint. */
if (light_trial_active && eax < 8) {
    uint32_t dev = MEM32(0x3D83C8);
    const uint8_t *header = ngb_ram_span(dev + 0x7A4, 8);
    if (header) {
        uint32_t table, capacity;
        memcpy(&table, header, 4); memcpy(&capacity, header + 4, 4);
        uint32_t index = eax, record = table + 144u * index;
        uint8_t *item = ngb_ram_span(record + 0x68, 40);
        /* The original prologue stores EDI below ESP. Do not move that
         * store ahead of aliases of the device, record, or argument. */
        const void *arg = ngb_ram_span(esp + 0x74, 4);
        void *spill = ngb_ram_span(esp - 4, 4);
        uintptr_t lo=(uintptr_t)spill, a=(uintptr_t)arg, h=(uintptr_t)header, q=(uintptr_t)item;
        if (index < capacity && item && arg && spill &&
            (lo+4<=h || h+8<=lo) && (lo+4<=q || q+40<=lo) &&
            (lo+4<=a || a+4<=lo) &&
            (lo+4<=(uintptr_t)ngb_fast_ram+0x3D83C8 || (uintptr_t)ngb_fast_ram+0x3D83CC<=lo)) {
            uint32_t flags,slot,enable;
            memcpy(&flags,item,4);memcpy(&slot,item+36,4);memcpy(&enable,arg,4);
            if ((flags & 1u) && (!!enable == (slot != UINT32_MAX))) {
                PUSH32(esp,edi);
                flags |= 4u;memcpy(item,&flags,4);
                edx=enable;ecx=slot;eax=0;
                ++light_trial_hits;
                goto loc_003C7996;
            }
        }
    }
}
