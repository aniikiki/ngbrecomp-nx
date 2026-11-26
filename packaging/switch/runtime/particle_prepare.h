#pragma once
#include "matrix.h"

/* These kernels run while the title builds the ordered list, before a draw
 * reaches the renderer. The unmodified instruction stream handles other memory
 * mappings and any point where a guest worker or interrupt can run. */
extern __attribute__((visibility("hidden"))) uint64_t ngb_reg_entries;
extern __attribute__((visibility("hidden"))) uint32_t ngb_reg_recent[32], ngb_reg_current_va;

static inline int particle_image(uint32_t address, unsigned bytes)
{
    return ngb_fast_ram && address >= (NGB_TICK_COUNT | 4095u) + 1 && address <= NGB_VM_BEGIN - bytes;
}

/* A particle's stack and its line buffer may straddle a VM page. Only accept
 * ordinary low RAM here. Each caller requests at most two adjacent pages. */
static inline unsigned char *particle_span(uint32_t address, unsigned bytes)
{
    if (!ngb_fast_ram || address > NGB_RAM_BYTES - bytes) return NULL;
    if (!particle_image(address, bytes) &&
        (ngb_fast_page_bytes[address >> 12] != 4096 ||
         ngb_fast_page_bytes[(address + bytes - 1) >> 12] != 4096)) return NULL;
    return ngb_fast_ram + address;
}

static inline int particle_disjoint(uint32_t a, unsigned an, uint32_t b, unsigned bn)
{
    return a + an <= b || b + bn <= a;
}

static inline int particle_quiet_polls(unsigned count)
{
    return !ngb_pending_dpcs && !(ngb_poll_mask & (ngb_poll_mask + 1u)) &&
           count <= ngb_poll_mask - (ngb_guest_polls & ngb_poll_mask);
}

static inline int particle_three_calls_ready(void)
{
    return particle_quiet_polls(3) && ngb_reg_entries >= 48 && ngb_reg_entries <= UINT64_MAX - 3;
}

/* A live particle checks its owner every tick. An actor with no parent has
 * no ownership chain to walk. Bit 1 without bit 4 requires a game callback. */
static inline int particle_unlinked_owner(void)
{
    const uint32_t actors = 0x4b4e50, stride = 0x2800;
    uint32_t offset = eax - actors;
    if (offset >= 32 * stride || offset % stride || !ngb_fast_ram ||
        ngb_fast_ram[eax + 0x27a0] != 0xff || esp < NGB_VM_BEGIN + 36) return 0;
    uint32_t index = offset / stride;
    unsigned flags = ngb_fast_ram[0x8b3eb8 + index];
    unsigned result = flags & 1, polls = result ? 4 : 5;
    if ((flags & 0x12) == 2 || !particle_quiet_polls(polls) ||
        ngb_reg_entries < 48 || ngb_reg_entries > UINT64_MAX - 2) return 0;
    unsigned char *stack = particle_span(esp - 36, 36);
    if (!stack) return 0;

    uint32_t spills[] = {eax, ebx, (offset & ~255u) | index, 0x001bdd45, edi,
                         esi, g_seh_ebp, ebx, ecx & 0xffffu};
    memcpy(stack, spills, sizeof spills);
    ecx &= 0xffffu;
    edx = flags & 0x10;
    eax = result;
    esp += 4;
    uint64_t entry = ngb_reg_entries;
    ngb_reg_recent[entry & 31] = 0x001bdd10;
    ngb_reg_recent[(entry + 1) & 31] = ngb_reg_current_va = 0x001bd9b0;
    ngb_reg_entries = entry + 2;
    ngb_guest_polls += polls;
    return 1;
}

static inline void particle_finish_calls(uint32_t first, uint32_t second, uint32_t last)
{
    uint64_t entry = ngb_reg_entries;
    ngb_reg_recent[entry & 31] = first;
    ngb_reg_recent[(entry + 1) & 31] = second;
    ngb_reg_recent[(entry + 2) & 31] = ngb_reg_current_va = last;
    ngb_reg_entries = entry + 3;
    ngb_guest_polls += 3;
}

/* Different native instruction schedules can select different NaN payloads.
 * Preserve the original instruction sequence for exceptional arithmetic. */
static inline int particle_finite3(const float v[3])
{
    return __builtin_isfinite(v[0]) && __builtin_isfinite(v[1]) && __builtin_isfinite(v[2]);
}

static inline int particle_move(void)
{
    if (!particle_image(esi, 0x15c)) return 0;
    unsigned char *p = ngb_fast_ram + esi;
    float pos[3], vel[3], rot[3], spin[3];
    memcpy(pos, p + 0x100, sizeof pos);
    memcpy(vel, p + 0x120, sizeof vel);
    memcpy(rot, p + 0x140, sizeof rot);
    memcpy(spin, p + 0x150, sizeof spin);
    pos[0] = vel[0] + pos[0];
    pos[1] += vel[1];
    pos[2] += vel[2];
    for (unsigned i = 0; i < 3; ++i) rot[i] += spin[i];
    if (!particle_finite3(pos) || !particle_finite3(rot)) return 0;
    memcpy(p + 0x100, pos, sizeof pos);
    memcpy(p + 0x140, rot, sizeof rot);
    xmm0 = XMM_SCALAR(rot[2]);
    return 1;
}

/* The two model paths call the same scale, translate and store routines.
 * Keep the fourth matrix components and the observable return frame intact.
 * If any of their three checkpoints could dispatch, use the original calls. */
static inline int particle_model_matrix(uint32_t bp, uint32_t return_address)
{
    const uint32_t matrix = 0x950180;
    if (!particle_image(ebx, 0x16c) || esp < NGB_VM_BEGIN + 8 ||
        !particle_disjoint(ebx, 0x16c, matrix, 64) ||
        !particle_three_calls_ready()) return 0;
    unsigned char *stack = particle_span(esp - 8, 0x68);
    if (!stack) return 0;
    unsigned char *p = ngb_fast_ram + ebx;
    float scale[3], pos[3];
    RecompXmm rows[4];
    memcpy(scale, p + 0x160, sizeof scale);
    memcpy(pos, p + 0x100, sizeof pos);
    memcpy(rows, ngb_fast_ram + matrix, sizeof rows);
    for (unsigned i = 0; i < 3; ++i) {
        rows[0].f[i] = scale[0] * rows[0].f[i];
        rows[1].f[i] = scale[1] * rows[1].f[i];
        rows[2].f[i] = rows[2].f[i] * scale[2];
        rows[3].f[i] = pos[i] + rows[3].f[i];
    }
    for (unsigned i = 0; i < 4; ++i) if (!particle_finite3(rows[i].f)) return 0;
    memcpy(ngb_fast_ram + matrix, rows, sizeof rows);
    memcpy(stack + 0x28, rows, sizeof rows);
    xmm0 = rows[0]; xmm1 = rows[1]; xmm2 = rows[2]; xmm3 = rows[3];
    eax = matrix;
    ecx = esp + 0x20;
    if (return_address == 0x00124dbf) {
        esi = ebx + 0x100;
        edx = ecx;
    }
    uint32_t destination = ecx;
    memcpy(stack + 4, &destination, 4);
    memcpy(stack, &return_address, 4);
    esp -= 4;
    g_ebp = g_seh_ebp = bp;
    particle_finish_calls(0x00305ca0, 0x00305b90, 0x000111f0);
    return 1;
}

/* The depth key uses base * camera. Retail saves the current world matrix,
 * installs the base, temporarily overwrites it with the product, then pops it.
 * Compute the same product and point without moving it through guest memory. */
static inline int particle_view_position(uint32_t bp)
{
    const uint32_t base = 0x950140, world = base + 64, camera = 0x977ce0, top = 0xd52688;
    if (!particle_image(edi, 0x10c) || esp < NGB_VM_BEGIN + 16 || !particle_three_calls_ready()) return 0;
    uint32_t point = edi + 0x100;
    uint32_t slot = MEM32(top) - 64;
    unsigned char *saved = particle_span(slot, 64);
    unsigned char *stack = particle_span(esp - 16, 0x60);
    if (!saved || !stack || !particle_disjoint(slot, 64, base, 128) ||
        !particle_disjoint(slot, 64, camera, 64) || !particle_disjoint(slot, 64, top, 4) ||
        !particle_disjoint(slot, 64, point, 12) || !particle_disjoint(slot, 64, esp - 16, 0x60) ||
        !particle_disjoint(point, 12, world, 64) || !particle_disjoint(point, 12, top, 4)) return 0;
    float base_rows[4][4];
    NgbMatrixRow camera_rows[4], row[4], term2, term3;
    memcpy(base_rows, ngb_fast_ram + base, sizeof base_rows);
    memcpy(camera_rows, ngb_fast_ram + camera, sizeof camera_rows);
    for (unsigned i = 0; i < 4; ++i) row[i] = ngb_product_row(base_rows[i], camera_rows, &term2, &term3);
    float xyz[3];
    memcpy(xyz, ngb_fast_ram + point, sizeof xyz);
    NgbMatrixRow result = ((xyz[0] * row[0] + row[3]) + xyz[1] * row[1]) + xyz[2] * row[2];
    for (unsigned i = 0; i < 4; ++i) if (!__builtin_isfinite(result[i])) return 0;
    uint32_t result_address = esp + 0x40;
    uint32_t calls[4] = {0x001257ed, world, slot, 0x00125845};
    memcpy(stack, calls, sizeof calls);
    memcpy(stack + 0x3c, &point, 4);
    memcpy(stack + 0x40, &result_address, 4);
    memcpy(stack + 0x50, &result, 16);
    memcpy(saved, ngb_fast_ram + world, 64);
    memcpy(&xmm0, saved, 16);      memcpy(&xmm1, saved + 16, 16);
    memcpy(&xmm2, saved + 32, 16); memcpy(&xmm3, saved + 48, 16);
    memcpy(&xmm4, &row[2], 16);    memcpy(&xmm5, &row[3], 16);
    eax = ecx = slot;
    g_ebp = g_seh_ebp = bp;
    particle_finish_calls(0x003058e0, 0x00328232, 0x00305950);
    return 1;
}

/* Style 0x62 copies a single packed colour to every vertex. Positions occupy
 * the first 0x100 bytes of the record. Other colour programs still run their
 * own interpolation and all paths share the original depth and ordering. */
static inline int particle_flat_vertices(void)
{
    if (!particle_image(edi, 0x231) || ngb_fast_ram[edi + 0x230] != 0x62 ||
        esp < NGB_VM_BEGIN || esp > NGB_RAM_BYTES - 0x28 || !particle_image(ebx, 4)) return 0;
    unsigned char *p = ngb_fast_ram + edi;
    uint16_t count;
    memcpy(&count, p + 0x21e, sizeof count);
    if (!count || count > 0x100 / 16 || !particle_quiet_polls(2u * count)) return 0;
    uint32_t array, colour;
    memcpy(&array, ngb_fast_ram + ebx, 4);
    unsigned length = 16u * count;
    unsigned char *out = particle_span(array, length);
    unsigned char *frame = particle_span(esp + 0x1c, 12);
    if (!out || !frame ||
        !particle_disjoint(array, length, edi, 0x231) ||
        !particle_disjoint(array, length, ebx, 4) ||
        !particle_disjoint(array, length, esp + 0x1c, 12)) return 0;
    memcpy(&colour, p + 0x20c, 4);
    for (unsigned i = 0; i < count; ++i) {
        memcpy(out + 16*i, p + 16*i, 12);
        memcpy(out + 16*i + 12, &colour, 4);
    }
    uint32_t cursor[] = {edi + 8 + length, count, length};
    memcpy(frame, cursor, sizeof cursor);
    eax = length; ecx = count; edx = count; esi = colour;
    ngb_guest_polls += 2u * count;
    return 1;
}
