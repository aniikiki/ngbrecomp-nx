#include "pgraph_boot.h"
#include "nv2a_vk/xemu/nv2a_regs.h"
#include "runtime.h"
#include "scene.h"
#include "contiguous.h"
#include "kernel/kernel.h"
#include <string.h>

static struct {
    uint32_t dma3d[11], dma_copy, dma_surface[2], blit_context[7], blit_operation;
    uint32_t constants[NV2A_VERTEXSHADER_CONSTANTS][4];
    uint32_t edge_flag, compress_depth, primitive, inline_words[128], inline_count;
    unsigned movie_frames, movie_changes;
    uint32_t movie_hash;
    uint32_t methods[0x2000/4], program[136][4], program_load;
} state;

#include "inline_draw.inc"

void ngb_pgraph_reset(void) { memset(&state, 0, sizeof(state)); }

uint32_t *ngb_pgraph_constant_word(uint32_t word)
{
    if (word/4 >= NV2A_VERTEXSHADER_CONSTANTS) ngb_stop("invalid RDI constant", word);
    uint32_t *constant = ngb_scene_constant(word);
    if (constant) return constant;
    return &state.constants[word/4][3-(word%4)];
}

static void release(uint32_t instance, uint32_t offset, uint32_t value)
{
    uint32_t desc[3];
    const void *src = ngb_instance_aperture(NGB_PRAMIN_BASE + instance, sizeof(desc));
    if (!src) ngb_stop("unmapped semaphore descriptor", instance);
    memcpy(desc, src, sizeof(desc));
    uint32_t cls = desc[0] & NV_DMA_CLASS;
    uint64_t phys = (uint64_t)((desc[2] & NV_DMA_ADDRESS) | (desc[0] >> 20)) + offset;
    uint32_t target = desc[0] & NV_DMA_TARGET;
    if ((cls != NV_DMA_TO_MEMORY_CLASS && cls != NV_DMA_IN_MEMORY_CLASS) ||
        (target != NV_DMA_TARGET_NVM && target != NV_DMA_TARGET_PCI))
        ngb_stop("unsupported semaphore DMA descriptor", desc[0]);
    if ((phys & 3) || (uint64_t)offset + 3 > desc[1] || phys + 4 > XBOX_CONTIG_SIZE)
        ngb_stop("invalid semaphore address", offset);
    void *dst = ngb_contiguous_pointer(XBOX_CONTIG_BASE + phys, 4);
    if (!dst) ngb_stop("unmapped semaphore target", (uint32_t)phys);
    memcpy(dst, &value, 4);
    char line[104];
    snprintf(line, sizeof(line), "PGRAPH semaphore physical=%08x value=%08x", (uint32_t)phys, value);
    ngb_kernel_log(line);
}

/* Rectangles and pitches are in logical framebuffer coordinates, as in
 * nv2a_vk. Guest tiles configure the memory controller (not Morton layout).
 * Only the single-sample, linear A8R8G8B8 and Z24S8 startup surfaces are
 * accepted here. Writes preserve unselected channels and row padding. */
static void clear_plane(uint32_t *r, uint32_t bits, int color)
{
    uint32_t *m = state.methods;
    uint32_t fmt = m[NV097_SET_SURFACE_FORMAT/4];
    if ((fmt & 0xff00) != 0x100 || (color ? (fmt & 15) != 8 : (fmt & 0xf0) != 0x20))
        ngb_stop("unsupported clear surface format", fmt);
    uint32_t clipx = m[NV097_SET_SURFACE_CLIP_HORIZONTAL/4], clipy = m[NV097_SET_SURFACE_CLIP_VERTICAL/4];
    if ((clipx & 65535) || (clipy & 65535)) ngb_stop("unsupported surface clip origin", clipx);
    unsigned width = clipx >> 16, height = clipy >> 16;
    uint32_t rect_x = r[NV_PGRAPH_CLEARRECTX/4], rect_y = r[NV_PGRAPH_CLEARRECTY/4];
    unsigned x0 = rect_x & 4095, x1 = ((rect_x >> 16)&4095)+1;
    unsigned y0 = rect_y & 4095, y1 = ((rect_y >> 16)&4095)+1;
    if (x1 > width) x1 = width;
    if (y1 > height) y1 = height;
    if (x1 <= x0 || y1 <= y0) return;
    uint32_t pitch = (m[NV097_SET_SURFACE_PITCH/4] >> (color ? 0 : 16)) & 65535;
    uint32_t offset = m[(color ? NV097_SET_SURFACE_COLOR_OFFSET : NV097_SET_SURFACE_ZETA_OFFSET)/4];
    uint32_t instance = state.dma3d[((color ? NV097_SET_CONTEXT_DMA_COLOR : NV097_SET_CONTEXT_DMA_ZETA)-0x180)/4];
    uint32_t desc[3]; void *obj = ngb_instance_aperture(NGB_PRAMIN_BASE+instance, sizeof(desc));
    if (!obj) ngb_stop("invalid clear DMA instance", instance);
    memcpy(desc, obj, sizeof(desc));
    uint32_t cls = desc[0] & NV_DMA_CLASS;
    if ((cls != NV_DMA_IN_MEMORY_CLASS && cls != NV_DMA_TO_MEMORY_CLASS) || (desc[0] & NV_DMA_TARGET))
        ngb_stop("unsupported clear DMA descriptor", desc[0]);
    uint64_t base = (uint64_t)((desc[2]&NV_DMA_ADDRESS) | (desc[0]>>20)) + offset;
    uint64_t bytes = (uint64_t)(y1-1)*pitch + x1*4;
    if ((base|pitch)&3 || width*4 > pitch || (uint64_t)offset+bytes > (uint64_t)desc[1]+1 ||
        base+bytes > XBOX_CONTIG_SIZE) ngb_stop("clear outside DMA bounds", offset);
    unsigned char *dst = ngb_contiguous_pointer(XBOX_CONTIG_BASE+base, bytes);
    if (!dst) ngb_stop("unmapped clear surface", (uint32_t)base);
    uint32_t mask = color ? ((bits&16 ? 0xff0000 : 0) | (bits&32 ? 0xff00 : 0) |
                              (bits&64 ? 0xff : 0) | (bits&128 ? 0xff000000u : 0)) :
                             ((bits&1 ? 0xffffff00u : 0) | (bits&2 ? 255u : 0));
    uint32_t value = r[(color ? NV_PGRAPH_COLORCLEARVALUE : NV_PGRAPH_ZSTENCILCLEARVALUE)/4];
    for (unsigned y=y0; y<y1; ++y) {
        uint32_t *row = (uint32_t *)(dst+(size_t)y*pitch);
        for (unsigned x=x0; x<x1; ++x) row[x] = (row[x]&~mask) | (value&mask);
    }
    char line[160];
    snprintf(line,sizeof(line),"PGRAPH clear %s base=%08x pitch=%u rect=%u,%u..%u,%u value=%08x mask=%08x",
        color?"color":"depth", (uint32_t)base,pitch,x0,y0,x1,y1,value,mask);
    ngb_kernel_log(line);
}

/* Retain state-only writes for later draw dispatch. No draw, report,
 * semaphore, interrupt, or clear is handled by this path. */
static int raster_state(uint32_t m)
{
    if ((m >= NV097_SET_TEXTURE_MATRIX_ENABLE && m < NV097_SET_TEXTURE_MATRIX_ENABLE + 4*4) ||
        (m >= NV097_SET_MATERIAL_EMISSION && m <= NV097_SET_MATERIAL_ALPHA) ||
        (m >= NV097_SET_SCENE_AMBIENT_COLOR && m < NV097_SET_SCENE_AMBIENT_COLOR + 3*4) ||
        (m >= NV097_SET_FOG_PARAMS && m < NV097_SET_FOG_PARAMS + 3*4)) return 1;
    if ((m >= 0x200 && m <= 0x214) || (m >= 0x300 && m <= 0x3a4) ||
        (m >= 0x3c0 && m <= 0x3f8 && (m&15) < 12) || (m >= 0xa20 && m < 0xa30) ||
        (m >= 0xa60 && m < 0xaa0) || (m >= 0xae0 && m < 0xb00) ||
        (m >= 0x1944 && m < 0x1980) || (m >= 0x1b00 && m < 0x1c00)) return 1;
    if ((m>=0x260 && m<0x280) || (m>=0x440 && m<0x7c0) ||
        (m>=0xaa0 && m<0xae0) || (m>=0x1720 && m<0x17a0) ||
        (m>=0x1e40 && m<=0x1e60)) return 1;
    switch (m) {
    case NV097_SET_COLOR_MATERIAL: case NV097_SET_FOG_MODE: case NV097_SET_FOG_GEN_MODE:
    case NV097_SET_LIGHT_CONTROL: case NV097_SET_POINT_SIZE: case NV097_SET_COMBINER_SPECULAR_FOG_CW0:
    case NV097_SET_COMBINER_SPECULAR_FOG_CW1: case NV097_SET_SHADER_STAGE_PROGRAM:
    case NV097_SET_FOG_ENABLE: case NV097_SET_LIGHT_ENABLE_MASK: case NV097_SET_SPECULAR_ENABLE:
    case 0x290: case 0x2a8: case 0x2b4: case 0x2c0: case 0x2e0:
    case 0x300: case 0x304: case 0x308: case 0x30c: case 0x310: case 0x9f8:
    case 0x147c: case 0x17bc: case 0x17c4: case 0x1d78: case 0x1d7c:
    case 0x1d84: case 0x1e6c: case 0x1e94: case 0x1e98: case 0x1ea0: return 1;
    default: return 0;
    }
}

void ngb_pgraph_method(uint32_t *r, uint32_t cls, uint32_t m, uint32_t v)
{
    /* Object parameters in 0x180..0x1ff have already been translated to
     * instance addresses by PFIFO. Launch and draw operations stay separate. */
    if (cls == 0x39 && m == 0x180) { state.dma_copy = v; return; }
    if (cls == NV_CONTEXT_SURFACES_2D && (m == 0x184 || m == 0x188)) {
        state.dma_surface[(m-0x184)/4] = v; return;
    }
    if (cls == NV_IMAGE_BLIT) {
        if (m >= 0x184 && m <= 0x19c) { state.blit_context[(m-0x184)/4] = v; return; }
        if (m == NV09F_SET_OPERATION) { state.blit_operation = v; return; }
    }
    if (cls == NV_CONTEXT_PATTERN && m == NV044_SET_MONOCHROME_COLOR0) {
        r[NV_PGRAPH_PATT_COLOR0/4] = v; return;
    }
    if (cls == NV_KELVIN_PRIMITIVE) {
        if (ngb_scene_method(r, m, v, state.constants)) return;
        if (m >= 0x180 && m <= 0x1a8 && m != 0x18c) { state.dma3d[(m-0x180)/4] = v; return; }
        if (m==NV097_SET_BEGIN_END) {
            if (v==6 && !state.primitive) { state.primitive=v; state.inline_count=0; return; }
            if (v || !state.primitive) ngb_stop("unsupported primitive",v);
            draw_strip();
            state.primitive=0;
            return;
        }
        if (m==NV097_INLINE_ARRAY) {
            if (!state.primitive || state.inline_count==128) ngb_stop("invalid inline array",state.inline_count);
            state.inline_words[state.inline_count++]=v;
            return;
        }
        if (raster_state(m)) { state.methods[m/4] = v; return; }
        if (m == NV097_NO_OPERATION && !v) return;
        /* Vertices are fetched directly from guest memory on each draw. */
        if (m == 0x1710 && !v) return; /* NV097_INVALIDATE_VERTEX_CACHE_FILE */
        if (m == NV097_WAIT_FOR_IDLE) return; /* all accepted work is synchronous */
        if (m == NV097_SET_TRANSFORM_PROGRAM_LOAD) { state.program_load = v; return; }
        if (m >= 0xb00 && m < 0xb80) {
            unsigned comp = (m/4)&3;
            if (state.program_load >= 136) ngb_stop("vertex program overflow", state.program_load);
            state.program[state.program_load][comp] = v;
            if (comp == 3) ++state.program_load;
            return;
        }
        if (m == NV097_CLEAR_SURFACE) {
            if (v & ~0xf3u) ngb_stop("unsupported clear mask", v);
            if (v & 3) clear_plane(r,v,0);
            if (v & 0xf0) clear_plane(r,v,1);
            return;
        }
        uint32_t row, comp;
        if (m >= 0x840 && m < 0x940) {
            uint32_t slot = (m-0x840)/4;
            row = NV_IGRAPH_XF_XFCTX_TG0MAT + (slot/16)*8 + (slot%16)/4; comp = slot%4;
        } else if (m >= 0x9d0 && m < 0x9e0) {
            row = NV_IGRAPH_XF_XFCTX_FOG; comp = (m-0x9d0)/4;
        } else if (m >= 0xa50 && m < 0xa60) {
            row = NV_IGRAPH_XF_XFCTX_EYEP; comp = (m-0xa50)/4;
        } else if (m >= 0xb80 && m < 0xc00) {
            row = (r[NV_PGRAPH_CHEOPS_OFFSET/4] & NV_PGRAPH_CHEOPS_OFFSET_CONST_LD_PTR) >> 8;
            comp = ((m-0xb80)/4)%4;
            if (row >= NV2A_VERTEXSHADER_CONSTANTS) ngb_stop("vertex constant overflow", row);
            if (comp == 3) r[NV_PGRAPH_CHEOPS_OFFSET/4] += 1u << 8;
        } else {
            uint32_t off, mask = UINT32_MAX;
            switch (m) {
            case NV097_FLIP_INCREMENT_WRITE: {
                uint32_t surface = r[NV_PGRAPH_SURFACE/4];
                unsigned mod = (surface >> 28) & 7;
                if (!mod) ngb_stop("invalid write flip modulo", surface);
                v = ((((surface >> 20) & 7) + 1) % mod) << 20;
                off = NV_PGRAPH_SURFACE; mask = NV_PGRAPH_SURFACE_WRITE_3D; break;
            }
            case NV097_SET_FLIP_READ: off = NV_PGRAPH_SURFACE; mask = NV_PGRAPH_SURFACE_READ_3D; v <<= 24; break;
            case NV097_SET_FLIP_WRITE: off = NV_PGRAPH_SURFACE; mask = NV_PGRAPH_SURFACE_WRITE_3D; v <<= 20; break;
            case NV097_SET_FLIP_MODULO: off = NV_PGRAPH_SURFACE; mask = NV_PGRAPH_SURFACE_MODULO_3D; v <<= 28; break;
            case NV097_SET_PROVOKING_VERTEX: off = NV_PGRAPH_CONTROL_3; mask = NV_PGRAPH_CONTROL_3_PROVOKING_VERTEX; break;
            case NV097_SET_SHADER_OTHER_STAGE_INPUT: off = NV_PGRAPH_SHADERCTL; mask = 0x0ffff000; break;
            case NV097_SET_SHADOW_ZSLOPE_THRESHOLD: off = NV_PGRAPH_SHADOWZSLOPETHRESHOLD; break;
            case NV097_SET_TRANSFORM_CONSTANT_LOAD:
                if (v >= NV2A_VERTEXSHADER_CONSTANTS) ngb_stop("invalid vertex constant load", v);
                off = NV_PGRAPH_CHEOPS_OFFSET; mask = NV_PGRAPH_CHEOPS_OFFSET_CONST_LD_PTR; v <<= 8; break;
            case NV097_SET_SEMAPHORE_OFFSET: off = NV_PGRAPH_SEMAPHOREOFFSET; break;
            case NV097_BACK_END_WRITE_SEMAPHORE_RELEASE:
                release(state.dma3d[(NV097_SET_CONTEXT_DMA_SEMAPHORE-0x180)/4], r[NV_PGRAPH_SEMAPHOREOFFSET/4], v);
                return;
            case NV097_SET_ZSTENCIL_CLEAR_VALUE: off = NV_PGRAPH_ZSTENCILCLEARVALUE; break;
            case NV097_SET_CLEAR_RECT_HORIZONTAL: off = NV_PGRAPH_CLEARRECTX; break;
            case NV097_SET_CLEAR_RECT_VERTICAL: off = NV_PGRAPH_CLEARRECTY; break;
            case NV097_SET_COLOR_CLEAR_VALUE: off = NV_PGRAPH_COLORCLEARVALUE; break;
            case 0x16bc: state.edge_flag = v & 1; return; /* NV097_SET_EDGE_FLAG */
            case 0x1d80: state.compress_depth = v & 1; return; /* NV097_SET_COMPRESS_ZBUFFER_EN */
            default: ngb_stop("unsupported PGRAPH class/method", cls << 16 | m);
            }
            r[off/4] = (r[off/4] & ~mask) | (v & mask);
            return;
        }
        state.constants[row][comp] = v;
        return;
    }
    ngb_stop("unsupported PGRAPH class/method", cls << 16 | m);
}
