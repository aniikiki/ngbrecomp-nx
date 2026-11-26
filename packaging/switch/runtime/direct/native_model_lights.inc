/* Shared model light submission (00317D10). The title reuses a stack
 * D3DLIGHT8 and leaves the three colour alpha words in it untouched. */
static int finish_disabled_lights(void)
{
    unsigned count = 8 - esi;
    if (count < 2 || ngb_pending_dpcs ||
        ngb_poll_mask - (ngb_guest_polls & ngb_poll_mask) < count) return 0;
    const uint8_t *flags = (const uint8_t *)ngb_ram_span(edi, (count - 1) * 0x7c + 4);
    if (!flags) return 0;
    for (unsigned i = 0; i < count; ++i) {
        uint32_t enabled;
        memcpy(&enabled, flags + i * 0x7c, sizeof enabled);
        if (enabled) return 0;
    }
    // The last disabled slot left these same arguments below ESP. If the
    // spills would change memory, keep the original stores and their order.
    const uint32_t expected[2] = {0x00317D81u, 0};
    const void *spill = ngb_ram_span(esp - 8, sizeof expected);
    if (!spill || memcmp(spill, expected, sizeof expected) ||
        !ngb_d3d_lights_already_disabled(esi)) return 0;
    ngb_guest_polls += count;
    eax = 0;
    esi = 8;
    edi = 0x9ac4f8;
    return 1;
}

static void model_pack_light(void)
{
    RECOMP_ENTRY(0x00318000u);
    ecx *= 0x7c;
    uint32_t record = 0x9ac0a0 + ecx;
    const uint8_t *src = (const uint8_t *)ngb_ram_span(record, 104);
    uint8_t *dst = (uint8_t *)ngb_ram_span(eax, 104);
    if (!src || !dst || ((uintptr_t)src < (uintptr_t)dst + 104 &&
                          (uintptr_t)dst < (uintptr_t)src + 104)) {
        // Preserve forward load/store order for overlapping spans and use
        // the normal guest accessor on stack or source page boundaries.
        for (unsigned i = 0; i < 26; ++i) {
            if (i == 4 || i == 8 || i == 12) continue;
            if (i >= 9 && i <= 11) MEM32(eax + i * 4) = 0;
            else if (i == 25) {
                ecx = MEM32(record + 100);
                MEM32(eax + 100) = ecx;
            } else {
                edx = MEM32(record + i * 4);
                if (i == 1) xmm0 = XMM_ZERO();
                MEM32(eax + i * 4) = edx;
            }
        }
    } else {
        memcpy(dst, src, 16);
        memcpy(dst + 20, src + 20, 12);
        memset(dst + 36, 0, 12);
        memcpy(dst + 52, src + 52, 52);
        xmm0 = XMM_ZERO();
        edx = MEM32(record + 96);
        ecx = MEM32(record + 100);
    }
    esp += 4;
}

int ngb_direct_model_lights(void)
{
    if (g_df || !ngb_d3d_native_enabled()) return 0;
    RECOMP_ENTRY(0x00317D10u);
    eax = MEM32(0x977bd4);
    esp -= 104;
    PUSH32(esp, esi);
    esi = 0x950140;
    PUSH32(esp, edi);
    if (eax != esi) {
        edi = MEM32(0x3d83c8) + 0xde0;
        eax = MEM32(0x3d83d0) | 0x200;
        MEM32(0x977bd4) = esi;
        const void *world = ngb_ram_span(esi, 64);
        void *device = ngb_ram_span(edi, 64);
        if (world && device && ((uintptr_t)world + 64 <= (uintptr_t)device ||
                               (uintptr_t)device + 64 <= (uintptr_t)world)) {
            memcpy(device, world, 64);
        } else {
            for (unsigned i = 0; i < 16; ++i) MEM32(edi + i * 4) = MEM32(esi + i * 4);
        }
        esi += 64;
        edi += 64;
        ecx = 0;
        MEM32(0x3d83d0) = eax;
    }
    mesh_poll();
    esi = 0;
    edi = 0x9ac118;
    do {
        if (!MEM32(edi) && finish_disabled_lights()) break;
        mesh_poll();
        uint32_t enabled = 0;
        if (MEM32(edi)) {
            eax = esp + 8;
            ecx = esi;
            PUSH32(esp, 0x00317D61u);
            model_pack_light();
            eax = MEM32(esp + 8);
            if (eax) {
                eax = esp + 8;
                PUSH32(esp, eax);
                PUSH32(esp, esi);
                PUSH32(esp, 0x00317D74u);
                d3d_hook(D3DF_D3DDevice_SetLight);
                enabled = 1;
            }
        }
        PUSH32(esp, enabled);
        eax = esi;
        PUSH32(esp, 0x00317D81u);
        d3d_hook(D3DF_D3DDevice_LightEnable);
        edi += 0x7c;
        ++esi;
    } while ((int32_t)edi < 0x9ac4f8);
    eax = MEM32(0x9ac480);
    int ambient_changed = eax != MEM32(0x97789c);
    POP32(esp, edi);
    POP32(esp, esi);
    if (ambient_changed) {
        ecx = MEM32(0x3d83d0) | 0x1000;
        MEM32(0x97789c) = eax;
        MEM32(0x3d83d0) = ecx;
        MEM32(0x3d85a4) = eax;
    }
    esp += 108;
    return 1;
}
