#pragma once
#include "recomp_funcs.h"

enum { MaterialLight, MaterialConstant1, MaterialConstant4, MaterialTexture, MaterialStream, MaterialCount };
extern uint64_t ngb_material_hits[MaterialCount];

/* SetLight's x87 normalization in the supported XBE. Within this range
 * every intermediate fits binary32, including the reciprocal-square-root
 * refinement. Keep the two argument spills and popped x87 slots observable. */
static inline int ngb_normalize_light(void)
{
    if (g_fp_control_word & 0x300) return 0;
    uint8_t *light = ngb_ram_span(ebx + 0x40, 0x38);
    uint8_t *scratch = ngb_ram_span(esp + 0x1c, 8);
    if (!light || !scratch) return 0;
    uintptr_t l = (uintptr_t)light, s = (uintptr_t)scratch;
    if (s < l + 0x38 && l < s + 8) return 0;
    /* Scratch and output are normally stack/heap. Keep the original order
     * if a caller places either on one of the math-constant pages. */
    uint32_t lp = ((ebx + 0x40) & 0x7fffffff) >> 12, sp = ((esp + 0x1c) & 0x7fffffff) >> 12;
    if (lp == 0x452 || lp == 0x414 || sp == 0x452 || sp == 0x414) return 0;
    float v[3];
    memcpy(v, light, sizeof(v));
    for (unsigned i = 0; i < 3; ++i) {
        if (v[i] != 0 && !(fabsf(v[i]) >= 0x1p-10f && fabsf(v[i]) <= 0x1p10f)) return 0;
        v[i] = -v[i];
    }
    float zz = v[2] * v[2];
    float length2 = (v[0] * v[0] + v[1] * v[1]) + zz;
    if (!length2) return 0;
    /* Fall back if the game patches its math constants. */
    if (MEMF(0x452860) != 0.47f || MEMF(0x452864) != 1.47f ||
        MEMF(0x4148D4) != 3.0f || MEMF(0x4148C0) != 0.5f) return 0;
    uint32_t bits;
    memcpy(&bits, &length2, 4);
    bits = (uint32_t)((int32_t)(0xbe800000u - bits) >> 1);
    float seed;
    memcpy(&seed, &bits, 4);
    float scaled = 0.47f * length2;
    float correction = (seed * seed) * scaled;
    float estimate = fabsf((1.47f - correction) * seed);
    float scale = ((3.0f - (estimate * estimate) * length2) * estimate) * 0.5f;
    for (unsigned i = 0; i < 3; ++i) v[i] *= scale;
    memcpy(light + 0x2c, v, sizeof(v));
    memcpy(scratch, &estimate, 4);
    memcpy(scratch + 4, &length2, 4);
    memcpy(&bits, &estimate, 4);
    ecx = bits;
    unsigned top = g_fp_top;
    g_fp_stack[(top - 1) & 7] = v[2];
    g_fp_stack[(top - 2) & 7] = v[1];
    g_fp_stack[(top - 3) & 7] = correction;
    g_fp_stack[(top - 4) & 7] = scaled;
    g_fp_stack[(top - 5) & 7] = zz;
    ++ngb_material_hits[MaterialLight];
    return 1;
}

/* The renderer reads the register file directly. Keep the same command
 * bytes too, including for user-recorded push buffers. Source and both
 * destinations must be ordinary disjoint RAM for these bulk transfers. */
static inline int ngb_write_constants(unsigned count)
{
    unsigned bytes = 16 * count;
    uint32_t put = eax - (12 + bytes);
    if (ecx > 192 - count || ((put | edx) & 3)) return 0;
    uint32_t target = 0x3d8678 + 16 * ecx;
    uint8_t *out = ngb_ram_span(put, 12 + bytes);
    uint8_t *constants = ngb_ram_span(target, bytes);
    const uint8_t *src = ngb_ram_span(edx, bytes);
    if (!src || !out || !constants) return 0;
    uintptr_t a = (uintptr_t)src, b = (uintptr_t)out, c = (uintptr_t)constants;
    uintptr_t cursor = (uintptr_t)ngb_fast_ram + 0x3d5f20;
    if ((a < b + bytes + 12 && b < a + bytes) || (a < c + bytes && c < a + bytes) ||
        (c < b + bytes + 12 && b < c + bytes) || (a < cursor + 4 && cursor < a + bytes) ||
        (b < cursor + 4 && cursor < b + bytes + 12)) return 0;
    MEM32(0x3D5F20) = eax;
    uint32_t header[] = {0x41ea4, ecx, ((bytes / 4) << 18) | 0xb80};
    memcpy(out, header, sizeof(header));
    memcpy(out + 12, src, bytes);
    memcpy(constants, src, bytes);
    if (count == 4) {
        memcpy(&mm0, src, 8);      memcpy(&mm1, src + 8, 8);
        memcpy(&mm2, src + 16, 8); memcpy(&mm3, src + 24, 8);
        memcpy(&mm4, src + 32, 8); memcpy(&mm5, src + 40, 8);
        memcpy(&mm6, src + 48, 8); memcpy(&mm7, src + 56, 8);
    }
    ++ngb_material_hits[count == 1 ? MaterialConstant1 : MaterialConstant4];
    ecx = target;
    return 1;
}

/* After SetTexture has released the old resource, retained the new one
 * and reserved the ring. The remaining XDK code handles dirty bits. */
static inline int ngb_write_texture_packet(uint32_t texture, uint32_t stage)
{
    if (stage >= 4 || ((eax | texture | esp) & 3)) return 0;
    const uint32_t *header = ngb_ram_span(texture, 20);
    uint32_t *stack = ngb_ram_span(esp + 0x10, 16);
    if (!header || !stack) return 0;
    uint32_t size = header[4];
    unsigned bytes = size ? 28 : 12;
    uint32_t *packet = ngb_ram_span(eax, bytes);
    uintptr_t p = (uintptr_t)packet, h = (uintptr_t)header, s = (uintptr_t)stack;
    if (!packet || (p < h + 20 && h < p + bytes) || (p < s + 16 && s < p + bytes) ||
        (s < h + 20 && h < s + 16)) return 0;
    uint32_t unit = stage << 6;
    packet[0] = 0x81b00 + unit;
    packet[1] = header[1];
    packet[2] = header[3];
    if (size) {
        uint32_t height = ((size >> 12) & 0xfff) + 1;
        stack[3] = height;
        packet[3] = 0x41b10 + unit;
        packet[4] = ((size >> 24) + 1) << 22;
        packet[5] = 0x41b1c + unit;
        packet[6] = (((size & 0xfff) + 1) << 16) | height;
        edi = stack[0];
    }
    ++ngb_material_hits[MaterialTexture];
    ebx = eax + bytes;
    return 1;
}

/* SetStreamSource has already retained the new buffer and saved the
 * caller's registers. Take the usual rebind, leaving the last release to
 * the original destructor and rejoining before the original poll. */
static inline unsigned ngb_bind_stream(uint32_t stride)
{
    if (eax >= 16 || ((esp | ecx) & 3)) return 0;
    uint32_t offset = eax * 12;
    uint32_t *slot = ngb_ram_span(0x3d93a8 + offset, 12);
    if (!slot) return 0;
    uint32_t old = slot[2];
    if (old) {
        if (old & 3) return 0;
        uint32_t *resource = ngb_ram_span(old, 12);
        uint32_t *stamp = ngb_ram_span(ecx + 0x2c, 4);
        uint32_t *spill = ngb_ram_span(esp - 4, 4);
        if (!resource || !stamp || !spill) return 0;
        uintptr_t h = (uintptr_t)resource, t = (uintptr_t)slot, s = (uintptr_t)spill;
        if ((h < t + 12 && t < h + 12) || (s < h + 12 && h < s + 4) ||
            (s < t + 12 && t < s + 4)) return 0;
        uint32_t references = resource[0] - 0x80000;
        if (!(references & 0x78ffff)) return 0;
        resource[2] = *stamp;
        *spill = edi;
        resource[0] = references;
        ecx = references;
    }
    unsigned path = stride == slot[0] ? 1 : 2;
    esi = offset;
    eax = MEM32(0x3D83D0);
    slot[0] = stride;
    slot[2] = ebx;
    ++ngb_material_hits[MaterialStream];
    return path;
}
