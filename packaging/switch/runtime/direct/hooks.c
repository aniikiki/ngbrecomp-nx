#ifndef NGB_DIAG
#define NGB_DIAG 1
#endif
#define RECOMP_GENERATED_CODE
#include "recomp_funcs.h"
#include "d3d_funcs.h"
#include "material.h"
#include "output.h"
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void d3d_hle_frame_wait(void);

int d3d_hle_call(int fn, uint32_t regs[8]);
void d3d_hle_after(int fn, const uint32_t regs[8]);
void d3d_visibility_begin(void);

/* The cooperative guest has one host thread. Charge overlapping calls once:
 * indexed draw first, then its mesh submission caller, then the rest of the frame. */
static struct {
    unsigned mesh_depth, index_depth, material_depth;
    uint64_t edge;
    unsigned long long indexed_ns, mesh_ns, other_ns, mesh_material_ns, other_material_ns;
    unsigned long long native, attempted, sampled, native_ns, controls, control_ns;
} index_time;

/* Publish a single tag so a suspended guest PC and its scope refer to
 * the same instant. The sampler reads it before resuming the worker. */
static atomic_uint sample_scope;
uint64_t ngb_material_hits[MaterialCount];
uint64_t ngb_native_material_meshes;

static void publish_scope(void)
{
    unsigned base = index_time.index_depth ? 2u : (index_time.mesh_depth != 0);
    atomic_store_explicit(&sample_scope, base | (index_time.material_depth ? 4u : 0u), memory_order_relaxed);
}

unsigned ngb_direct_sample_scope(void)
{
    return atomic_load_explicit(&sample_scope, memory_order_relaxed);
}

static int material_call(int fn)
{
    switch (fn) {
    case D3DF_D3DDevice_SetTexture:
    case D3DF_D3DDevice_SetStreamSource:
    case D3DF_D3DDevice_SetLight:
    case D3DF_D3DDevice_LightEnable:
    case D3DF_D3DDevice_SetVertexShaderConstant1:
    case D3DF_D3DDevice_SetVertexShaderConstant4:
        return 1;
    default:
        return 0;
    }
}

int ngb_direct_detail_frame;
static int full_timing;
static unsigned measured_frames;

static void charge_scope(void)
{
    if (!ngb_direct_detail_frame) return;
    uint64_t now = ngb_elapsed_ns();
    uint64_t delta = now - index_time.edge;
    index_time.edge = now;
    if (index_time.index_depth) index_time.indexed_ns += delta;
    else if (index_time.mesh_depth) index_time.mesh_ns += delta;
    else index_time.other_ns += delta;
    if (index_time.material_depth && !index_time.index_depth) {
        if (index_time.mesh_depth) index_time.mesh_material_ns += delta;
        else index_time.other_material_ns += delta;
    }
}

/* Take one complete frame in every group of sixteen. Rotate the phase so
 * alternating work (odd/even skin or effects updates) cannot alias the sample. */
void ngb_direct_timing_flip(unsigned completed)
{
    charge_scope();
    measured_frames += ngb_direct_detail_frame;
    unsigned group = completed >> 4;
    ngb_direct_detail_frame = full_timing || ((completed & 15u) == ((group * 9u) & 15u));
    if (ngb_direct_detail_frame) index_time.edge = ngb_elapsed_ns();
}

void ngb_direct_mesh_scope(int enter)
{
    charge_scope();
    if (enter) { ++index_time.mesh_depth; ++ngb_native_material_meshes; }
    else --index_time.mesh_depth;
    publish_scope();
}

void ngb_direct_index_reset(void)
{
    unsigned mesh = index_time.mesh_depth, index = index_time.index_depth, material = index_time.material_depth;
    memset(&index_time, 0, sizeof(index_time));
    memset(ngb_material_hits, 0, sizeof(ngb_material_hits));
    index_time.mesh_depth = mesh;
    index_time.index_depth = index;
    index_time.material_depth = material;
    publish_scope();
    const char *mode = getenv("NGB_RENDER_FULL_TIMING");
    full_timing = mode && !strcmp(mode, "1");
    measured_frames = 0;
    ngb_direct_detail_frame = NGB_DIAG;
    index_time.edge = ngb_elapsed_ns();
}

void ngb_direct_index_close(void)
{
    memset(&index_time, 0, sizeof(index_time));
    ngb_direct_detail_frame = 0;
    publish_scope();
}

void ngb_direct_index_report(void)
{
    char line[200];
    snprintf(line, sizeof(line), "3D scene sampled_frames=%u indexed_us=%llu mesh_excluding_index_us=%llu remaining_us=%llu",
             measured_frames, index_time.indexed_ns / 1000, index_time.mesh_ns / 1000, index_time.other_ns / 1000);
    ngb_kernel_log(line);
    snprintf(line, sizeof(line), "3D scene sampled material setters in_mesh_us=%llu outside_mesh_us=%llu",
             index_time.mesh_material_ns / 1000, index_time.other_material_ns / 1000);
    ngb_kernel_log(line);
    snprintf(line, sizeof(line), "3D scene material fast light=%llu vs1=%llu vs4=%llu texture=%llu stream=%llu",
             (unsigned long long)ngb_material_hits[MaterialLight], (unsigned long long)ngb_material_hits[MaterialConstant1],
             (unsigned long long)ngb_material_hits[MaterialConstant4], (unsigned long long)ngb_material_hits[MaterialTexture],
             (unsigned long long)ngb_material_hits[MaterialStream]);
    ngb_kernel_log(line);
    snprintf(line, sizeof(line), "3D scene XDK strip candidates=%llu native=%llu native_samples=%llu native_ns=%llu ref_samples=%llu ref_ns=%llu",
             index_time.attempted, index_time.native, index_time.sampled, index_time.native_ns,
             index_time.controls, index_time.control_ns);
    ngb_kernel_log(line);
}

int ngb_direct_index_capture_ready(uint32_t stack);
int ngb_direct_compact_indices(uint32_t stack, uint32_t count);

void ngb_direct_index_reference_done(uint64_t start)
{
    index_time.control_ns += ngb_elapsed_ns() - start;
    ++index_time.controls;
}

int ngb_direct_try_indexed(uint64_t *reference_start)
{
    /* HLE has already captured this strip. Only take the path where SetStateVB
     * is also taken, the PUT reservation fits, and no fence needs servicing. */
    if (!ngb_direct_index_capture_ready(esp)) return 0;
    unsigned sample = index_time.attempted++ % 32;
    uint64_t start = sample == 1 ? ngb_elapsed_ns() : 0;
    uint32_t device = MEM32(0x3D83C8);
    uint32_t *dev = ngb_ram_span(device, 32);
    if (!dev || ((esp | device) & 3)) return 0;
    uint32_t flags = dev[2], put = dev[0], limit = dev[1];
    if ((put & 3) || (flags & 0x1804) || put > UINT32_MAX - 0x824 ||
        limit > UINT32_MAX - 0x200 || put + 0x824 >= limit + 0x200) return 0;
    uint32_t *ring = ngb_ram_span(put, 16);
    uint32_t *stack = ngb_ram_span(esp - 32, 48);
    if (!ring || !stack) return 0;
    /* When mappings alias, preserve the lifted code's exact load/store order. */
    uintptr_t a = (uintptr_t)dev, b = (uintptr_t)ring, c = (uintptr_t)stack;
    if ((a < b + 16 && b < a + 32) || (b < c + 48 && c < b + 16) ||
        (a < c + 48 && c < a + 32)) return 0;
    if (sample == 0) {
        *reference_start = ngb_elapsed_ns();
        return 0;
    }
    if (!ngb_direct_compact_indices(esp, stack[10])) return 0;
    /* Match the guest call frame, including the published EBP and the spill
     * words the translated function leaves below its incoming stack pointer. */
    stack[0] = 0x003C9B5B;
    stack[1] = device;
    stack[2] = dev[7];
    stack[3] = esi;
    stack[4] = ebx;
    stack[5] = device;
    stack[7] = g_ebp;
    g_ebp = g_seh_ebp = esp - 4;
    ring[0] = ring[2] = 0x417FC;
    ring[1] = stack[9];
    ring[3] = 0;
    eax = flags | 0x800;
    ecx = device;
    edx = eax & ~0x1800u;
    dev[0] = put + 16;
    dev[2] = edx;
    esp += 16;
    ++index_time.native;
    if (sample == 1) {
        index_time.native_ns += ngb_elapsed_ns() - start;
        ++index_time.sampled;
    }
    return 1;
}

static void track_draw_call(int fn, int entering)
{
    unsigned *depth;
    if (fn == D3DF_D3DDevice_DrawIndexedVertices) depth = &index_time.index_depth;
    else if (material_call(fn)) depth = &index_time.material_depth;
    else return;
    charge_scope();
    if (entering) ++*depth;
    else --*depth;
    publish_scope();
}

int d3d_hook(int fn)
{
    uint32_t regs[] = {eax, ecx, edx, ebx, esp, g_ebp, esi, edi};
    if (fn == D3DF_Direct3D_CreateDevice) {
        const char *mode = getenv("NGB_D3D_THREAD");
        if (!mode || strcmp(mode, "0")) {
            /* Keep the 2 MiB ring used by the device performance baseline. */
            if (MEM32(0x3D958C) < 2u * 1024 * 1024) MEM32(0x3D958C) = 2u * 1024 * 1024;
            MEM32(0x3D9588) = NGB_DIRECT_KICKOFF_KIB * 1024;
        }
    }
    track_draw_call(fn, 1);
    int took = d3d_hle_call(fn, regs);
    if (took) track_draw_call(fn, 0);
    if (fn == D3DF_D3DDevice_Swap) d3d_hle_frame_wait();
    if (!took) return 0;
    eax = regs[0]; ecx = regs[1]; edx = regs[2]; ebx = regs[3];
    esp = regs[4]; g_ebp = regs[5]; esi = regs[6]; edi = regs[7];
    return 1;
}

int d3d_hle_native_address(uint32_t address, uint32_t regs[8]);
int ngb_d3d_native_entry(uint32_t address)
{
    if (!ngb_d3d_native_enabled()) ngb_stop("native graphics objects require native mode", address);
    uint32_t regs[] = {eax, ecx, edx, ebx, esp, g_ebp, esi, edi};
    int took = d3d_hle_native_address(address, regs);
    eax = regs[0]; ecx = regs[1]; edx = regs[2]; ebx = regs[3];
    esp = regs[4]; g_ebp = regs[5]; esi = regs[6]; edi = regs[7];
    return took;
}

int ngb_direct_material_fixed(void)
{
    if (g_df || !ngb_d3d_material_fixed(esi)) return 0;
    esp += 4;
    return 1;
}

int ngb_direct_material_texture(void)
{
    if (g_df || !ngb_d3d_material_texture(eax, edi)) return 0;
    esp += 4;
    return 1;
}

#include "native_mesh.inc"
#include "native_model.inc"

void d3d_after(int fn)
{
    const uint32_t regs[] = {eax, ecx, edx, ebx, esp, g_ebp, esi, edi};
    d3d_hle_after(fn, regs);
    track_draw_call(fn, 0);
    if (fn == D3DF_Direct3D_CreateDevice) {
        char line[120];
        snprintf(line, sizeof(line), "3D scene Direct3D command buffer=%u KiB kick-off=%u KiB",
                 MEM32(0x3D958C) / 1024, MEM32(0x3D9588) / 1024);
        ngb_kernel_log(line);
    }
}

void d3d_visibility_hook(void)
{
    d3d_visibility_begin();
}
