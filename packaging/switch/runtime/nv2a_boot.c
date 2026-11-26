#include <stdatomic.h>
#include "services.h"
#include "scene.h"
#include "ohci_boot.h"
#include "scanout.h"
#include "nv2a_boot.h"
#ifdef NGB_DIRECT3D
#include "direct/output.h"
#endif
#include "pgraph_boot.h"
#include "menu_gpu.h"
#include "runtime.h"
#include "contiguous.h"
#include <string.h>
#include <stdatomic.h>
#include "kernel/kernel.h"
#include "nv2a_vk/xemu/nv2a_regs.h"

enum {
    ENGINE_ENABLE = 0xfd000000u + NV_PMC_ENABLE,
    ENGINE_TIMER = 1u << 16, ENGINE_FB = 1u << 20, ENGINE_CRTC = 1u << 24,
    ENGINE_MASK = NV_PMC_ENABLE_PFIFO | NV_PMC_ENABLE_PGRAPH | ENGINE_TIMER | ENGINE_FB | ENGINE_CRTC,
    CORE_PLL = 0xfd680000u + NV_PRAMDAC_NVPLL_COEFF,
    MEMORY_PLL = 0xfd680000u + NV_PRAMDAC_MPLL_COEFF,
    VIDEO_PLL = 0xfd680000u + NV_PRAMDAC_VPLL_COEFF,
    TIMER_NUM = 0xfd009000u + NV_PTIMER_NUMERATOR,
    TIMER_DEN = 0xfd009000u + NV_PTIMER_DENOMINATOR,
    TIMER_ALARM = 0xfd009000u + NV_PTIMER_ALARM_0,
    TIMER_LOW = 0xfd009000u + NV_PTIMER_TIME_0,
    TIMER_HIGH = 0xfd009000u + NV_PTIMER_TIME_1,
    TIMER_STATUS = 0xfd009000u + NV_PTIMER_INTR_0,
    FIFO_RAMHT = 0xfd002000u + NV_PFIFO_RAMHT,
    FIFO_RAMFC = 0xfd002000u + NV_PFIFO_RAMFC,
    FB_NVM = 0xfd100214u,
    CRTC_INDEX = 0xfd6013d4u, CRTC_DATA = 0xfd6013d5u,
    CRTC_CONFIG = 0xfd600804u,
    GRAPH_CTX_TABLE = 0xfd400000u + NV_PGRAPH_CHANNEL_CTX_TABLE,
    FB_CONFIG0 = 0xfd100000u + NV_PFB_CFG0,
    FB_CONFIG1 = 0xfd100204u,
    BUS_DEBUG = 0xfd001218u,
    MASTER_STATUS = 0xfd000000u + NV_PMC_INTR_0,
    MASTER_IRQ = 0xfd000000u + NV_PMC_INTR_EN_0,
    CRTC_STATUS = 0xfd600000u + NV_PCRTC_INTR_0,
    PCI_AGP_COMMAND = 0xfd00184cu,
    PCI_LATENCY = 0xfd00180cu,
    PCI_ROM = 0xfd001830u,
    PCI_ID = 0xfd001000u + NV_PBUS_PCI_NV_0,
    PCI_COMMAND = 0xfd001000u + NV_PBUS_PCI_NV_1,
    PCI_CLASS_REV = 0xfd001000u + NV_PBUS_PCI_NV_2,
    TIMER_IRQ = 0xfd009000u + NV_PTIMER_INTR_EN_0,
    CRTC_IRQ = 0xfd600000u + NV_PCRTC_INTR_EN_0,
    MEMORY_SIZE = 0xfd100000u + NV_PFB_CSTATUS,
};

static uint32_t command, timer_irq, crtc_irq, master_irq, crtc_status, pci_latency;
static uint8_t palette[256][3];
static unsigned palette_component;
static uint8_t crtc_index, crtc_regs[256];
static uint32_t crtc_config, graph_ctx_table, agp_command;
static uint32_t video_regs[0x1000 / 4], fifo_regs[0x2000 / 4];

static uint32_t graph_regs[0x2000 / 4], fb_regs[0x328 / 4];
static uint32_t rdi_index, tile_rdi[0x2000 / 4], pipe_rdi[16], debug_rdi[2];
#ifdef NGB_DIRECT3D
#include "direct/output.h"
/* Render thread publishes the last drawn PUT. Only the guest thread may
 * execute emulated methods, raise interrupts or update the guest registers. */
static _Atomic uint64_t render_gate;
static _Atomic uint32_t guest_put;
void (*nv2a_user_read_hook)(void);
uint32_t nv2a_pfifo_put(void) { return atomic_load(&guest_put); }
void nv2a_pfifo_gate(int on, uint32_t put) {
    atomic_store(&render_gate, ((uint64_t)(on != 0) << 32) | put);
}
static bool servicing_dma, deferred_dma;
static void service_dma(void);
#endif
static int context_wait, flip_wait;
static uint32_t scanout_start;
static uint64_t fifo_ns, fifo_start;
#ifdef NGB_DIRECT3D
static uint64_t direct_batched_words;
uint64_t ngb_direct_fifo_batched_words(void) { return direct_batched_words; }
#endif

static int flip_ready(void)
{
    uint32_t surface = graph_regs[NV_PGRAPH_SURFACE/4];
    return ((surface >> 20) & 7) != ((surface >> 24) & 7);
}
static uint32_t batch_first, packet_count, param_count;

static void reset_graph(void)
{
    memset(graph_regs, 0, sizeof(graph_regs));
    context_wait = flip_wait = 0;
    scanout_start = 0;
    ngb_pgraph_reset();
    memset(debug_rdi, 0, sizeof(debug_rdi));
    memset(pipe_rdi, 0, sizeof(pipe_rdi));
    memset(tile_rdi, 0, sizeof(tile_rdi));
    rdi_index = graph_ctx_table = 0;
}

/* RDI indexes are byte offsets; accessing DATA advances the selected bank. */
static uint32_t *next_rdi_word(void)
{
    uint32_t bank = rdi_index & NV_PGRAPH_RDI_INDEX_SELECT;
    int constants = bank == RDI_INDEX_VTX_CONSTANTS0 << 16 || bank == RDI_INDEX_VTX_CONSTANTS1 << 16;
    if (rdi_index == 0xe00050 || rdi_index == 0xdf0008) {
        unsigned index = rdi_index == 0xdf0008;
        rdi_index += 4;
        return &debug_rdi[index];
    }
    if (!constants && bank != 0xea0000 && bank != 0x3d0000)
        ngb_stop("unsupported PGRAPH RDI bank", rdi_index);
    uint32_t offset = rdi_index & NV_PGRAPH_RDI_INDEX_ADDRESS;
    rdi_index = (rdi_index & ~NV_PGRAPH_RDI_INDEX_ADDRESS) |
                ((offset + 4) & NV_PGRAPH_RDI_INDEX_ADDRESS);
    if (constants) return ngb_pgraph_constant_word(offset/4);
    if (bank == 0xea0000) return &tile_rdi[offset / 4];
    if (offset / 4 >= 16) ngb_stop("unsupported pipe RDI offset", offset);
    return &pipe_rdi[offset / 4];
}

/* Storage registers used while the channels are idle. Registers with launch,
 * status, or interrupt side effects must be handled by their own paths. */
static uint32_t *setup_register(uint32_t va)
{
    uint32_t off = va - 0xfd008000u;
    if (!(off & 3) && (off == 0x88 || off == 0x8c ||
        (off >= 0x910 && off <= 0x944))) return &video_regs[off / 4];
    off = va - 0xfd002000u;
    switch (off) {
    case NV_PFIFO_CACHE1_PUT: case NV_PFIFO_CACHE1_GET:
    case NV_PFIFO_CACHE1_DMA_PUT: case NV_PFIFO_CACHE1_DMA_GET:
    case NV_PFIFO_CACHE1_DMA_STATE: case NV_PFIFO_MODE:
    case 0x1058: case 0x1258: case 0x508: case 0x50c: case 0x410: case 0x420:
        return &fifo_regs[off / 4];
    }
    switch (off) {
    case NV_PFIFO_CACHE1_DMA_GET_JMP_SHADOW:
    case 0x40: case 0x44: case 0x4c: case 0x500: case 0x1000: case 0x1050:
    case NV_PFIFO_INTR_EN_0: case NV_PFIFO_CACHE1_PUSH0: case NV_PFIFO_CACHE1_PUSH1:
    case NV_PFIFO_CACHE1_DMA_FETCH: case NV_PFIFO_CACHE1_DMA_PUSH:
    case NV_PFIFO_CACHE1_DMA_INSTANCE: case NV_PFIFO_CACHE1_REF:
    case NV_PFIFO_CACHE1_DMA_SUBROUTINE: case NV_PFIFO_CACHE1_PULL0:
    case NV_PFIFO_CACHE1_PULL1: case NV_PFIFO_CACHE1_ENGINE:
    case 0x1230: case 0x1260: case 0x1264: case 0x1268: case 0x126c:
        return &fifo_regs[off / 4];
    }
    off = va - 0xfd400000u;
    if (!(off & 3) && off >= NV_PGRAPH_CTX_SWITCH5 && off < NV_PGRAPH_CTX_CACHE5 + 32)
        return &graph_regs[off/4];
    switch (off) {
    case NV_PGRAPH_PATT_COLOR0: case NV_PGRAPH_COLORCLEARVALUE: case NV_PGRAPH_CONTROL_3:
    case NV_PGRAPH_SHADERCTL: case NV_PGRAPH_SEMAPHOREOFFSET: case NV_PGRAPH_SHADOWZSLOPETHRESHOLD:
    case NV_PGRAPH_CHEOPS_OFFSET:
    case 0x80: case 0x84: case 0x8c: case 0x90: case 0x94: case 0x98: case 0x9c:
    case NV_PGRAPH_TRAPPED_DATA_LOW: case NV_PGRAPH_ZSTENCILCLEARVALUE: case NV_PGRAPH_TRAPPED_ADDR: case NV_PGRAPH_NSOURCE: case NV_PGRAPH_SURFACE:
    case 0x880: case 0xb80: case 0xb84: case 0xb88: case NV_PGRAPH_INTR_EN:
    case NV_PGRAPH_CTX_CONTROL: case NV_PGRAPH_CTX_USER:
    case 0x14c: case 0x150: case 0x154: case 0x158: case 0x764:
    case NV_PGRAPH_FIFO: case NV_PGRAPH_CHANNEL_CTX_POINTER:
        return &graph_regs[off / 4];
    }
    if (!(off & 3) && ((off >= 0x900 && off < 0x980 && (off & 15) <= 8) ||
                        (off >= 0x980 && off <= 0x9a8))) return &graph_regs[off / 4];
    off = va - 0xfd100000u;
    if (!(off & 3) && ((off >= NV_PFB_TILE && off < 0x2c0 && (off & 15) <= 8) ||
                        (off >= 0x300 && off <= 0x31c) || off == 0x324))
        return &fb_regs[off / 4];
    if (va == CRTC_CONFIG) return &crtc_config;
    if (va == GRAPH_CTX_TABLE) return &graph_ctx_table;
    return NULL;
}

static uint64_t frame;
static uint32_t ramht, ramfc, fb_nvm;
static uint32_t engines, timer_num, timer_den, alarm_low, timer_status;
static uint64_t timer_epoch, timer_base, alarm_tick;

/* Reset PLL values from nv2a_vk/host/nv2a_host.c. NVPLL N=28, M=1, P=1. */
static uint32_t pll_coeff(uint32_t va)
{
    switch (va) {
    case CORE_PLL: return 0x00011c01;
    case MEMORY_PLL: return 0;
    case VIDEO_PLL: return 0x0003c20d;
    default: ngb_stop("unsupported NV2A PLL read", va);
    }
}

static uint64_t timer_ticks(uint64_t now)
{
    if (!(engines & ENGINE_TIMER) || !timer_num) return timer_base;
    const uint64_t core_hz = NV2A_CRYSTAL_FREQ * 14ull;
    __uint128_t scaled = (__uint128_t)(now - timer_epoch) * core_hz * timer_den;
    return timer_base + (uint64_t)(scaled / (1000000000ull * timer_num));
}

/* Low 5 time bits are zero. A programmed low-word match recurs every 2^27 ticks. */
static uint64_t next_alarm(uint64_t ticks)
{
    const uint64_t period = 1ull << 27;
    uint64_t target = (ticks & ~(period - 1)) | (alarm_low >> 5);
    return target > ticks ? target : target + period;
}

static void sample_alarm(void)
{
    if (!(engines & ENGINE_TIMER) || !(timer_irq & NV_PTIMER_INTR_0_ALARM)) return;
    uint64_t ticks = timer_ticks(ngb_elapsed_ns());
    if (ticks >= alarm_tick) {
        timer_status |= NV_PTIMER_INTR_0_ALARM;
        alarm_tick = next_alarm(ticks);
    }
}

static void reset_timer(void)
{
    timer_num = timer_den = 1;
    timer_status = timer_irq = alarm_low = 0;
    timer_epoch = timer_base = alarm_tick = 0;
}

static void sample_vblank(void)
{
    /* The bootstrap display clock runs at 60 Hz until mode setting is wired. */
    uint64_t current = ngb_elapsed_ns() / 16666667u;
    if ((engines & ENGINE_CRTC) && current != frame) {
        crtc_status |= NV_PCRTC_INTR_0_VBLANK;
        if (scanout_start) ngb_scanout_refresh(scanout_start);
    }
    frame = current;
}

uint32_t ngb_nv2a_field(void)
{
    sample_vblank();
    return (uint32_t)(frame & 1);
}

static uint32_t master_status(void)
{
    uint32_t status = (crtc_status & crtc_irq) ? NV_PMC_INTR_0_PCRTC : 0;
    if (graph_regs[NV_PGRAPH_INTR / 4] & graph_regs[NV_PGRAPH_INTR_EN / 4]) status |= NV_PMC_INTR_0_PGRAPH;
    if (fifo_regs[NV_PFIFO_INTR_0 / 4] & fifo_regs[NV_PFIFO_INTR_EN_0 / 4]) status |= NV_PMC_INTR_0_PFIFO;
    sample_alarm();
    if (timer_status & timer_irq) status |= NV_PMC_INTR_0_PTIMER;
    return status;
}

uint32_t ngb_nv2a_irq_pending(void)
{
#ifdef NGB_DIRECT3D
    if (deferred_dma) service_dma();
#endif
    sample_vblank();
    return (master_irq & NV_PMC_INTR_EN_0_HARDWARE) ? master_status() : 0;
}

void ngb_nv2a_reset(void)
{
#ifdef NGB_DIRECT3D
    deferred_dma = servicing_dma = false;
    atomic_store(&render_gate, 0);
    atomic_store(&guest_put, 0);
#endif
    command = timer_irq = crtc_irq = master_irq = crtc_status = pci_latency = 0;
    reset_graph();
    memset(fb_regs, 0, sizeof(fb_regs));
    crtc_index = 0;
    memset(palette, 0, sizeof(palette)); palette_component = 0;
    memset(crtc_regs, 0, sizeof(crtc_regs));
    crtc_regs[NV_PRMCIO_INTERLACE_MODE] = NV_PRMCIO_INTERLACE_MODE_DISABLED;
    memset(video_regs, 0, sizeof(video_regs));
    memset(fifo_regs, 0, sizeof(fifo_regs));
    crtc_config = graph_ctx_table = agp_command = 0;
    engines = 0;
    frame = 0;
    fifo_ns = fifo_start = 0;
#ifdef NGB_DIRECT3D
    direct_batched_words = 0;
#endif
    ramht = ramfc = fb_nvm = 0;
    reset_timer();
}

static void trace(const char *operation, uint32_t va, uint32_t value)
{
    if (!ngb_mmio_trace_enabled()) return;
    char line[80];
    snprintf(line, sizeof(line), "NV2A %s addr=%08x value=%08x", operation, va, value);
    ngb_kernel_log(line);
}

/* The active USER DMA channel aliases CACHE1. Only consume commands whose
 * effects we implement; a method packet must reach a renderer before GET
 * can advance past it. */
static uint32_t user_register(uint32_t va)
{
    uint32_t channel = (va - 0xfd800000u) >> 16;
    uint32_t active = fifo_regs[NV_PFIFO_CACHE1_PUSH1 / 4];
    if (channel >= 32 || (active & 31u) != channel || !(active & NV_PFIFO_CACHE1_PUSH1_MODE) ||
        !(fifo_regs[NV_PFIFO_MODE / 4] & (1u << channel)))
        ngb_stop("inactive NV2A USER DMA channel", va);
    switch (va & 0xffffu) {
    case NV_USER_DMA_PUT: return NV_PFIFO_CACHE1_DMA_PUT;
    case NV_USER_DMA_GET: return NV_PFIFO_CACHE1_DMA_GET;
    case NV_USER_REF: return NV_PFIFO_CACHE1_REF;
    default: ngb_stop("unsupported NV2A USER register", va);
    }
}

static void *dma_commands(uint32_t physical, size_t bytes)
{
    uint32_t va = XBOX_CONTIG_BASE + physical;
    if (!ngb_scene_active) return ngb_contiguous_pointer(va, bytes);
    void *ptr = ngb_contiguous_pointer_raw(va, bytes);
    if (ptr) ngb_scene_read_targets(physical, bytes);
    return ptr;
}

#ifdef NGB_DIRECT3D
// Contiguous Kelvin methods consumed by the Direct3D draw hooks. The first
// parameter still dispatches normally to restore the subchannel context.
static unsigned direct_state_words(uint32_t method)
{
    if (method >= NV097_SET_TRANSFORM_PROGRAM && method < NV097_SET_TRANSFORM_CONSTANT + 128)
        return (NV097_SET_TRANSFORM_CONSTANT + 128 - method) / 4;
    if (method >= NV097_SET_VERTEX_DATA_ARRAY_OFFSET && method < NV097_SET_VERTEX_DATA_ARRAY_FORMAT + 64)
        return (NV097_SET_VERTEX_DATA_ARRAY_FORMAT + 64 - method) / 4;
    if (method >= NV097_SET_ALPHA_TEST_ENABLE && method <= NV097_SET_DEPTH_FUNC)
        return (NV097_SET_DEPTH_FUNC + 4 - method) / 4;
    if (method >= NV097_SET_VERTEX_DATA4F_M && method < NV097_SET_TEXTURE_OFFSET)
        return (NV097_SET_TEXTURE_OFFSET - method) / 4;
    if (method >= NV097_SET_TEXTURE_OFFSET && method < NV097_SET_TEXTURE_OFFSET + 4 * 64)
        return (NV097_SET_TEXTURE_OFFSET + 4 * 64 - method) / 4;
    return 0;
}
#else
static int batch_state_method(uint32_t method)
{
    return (method >= NV097_SET_TRANSFORM_PROGRAM && method < NV097_SET_TRANSFORM_CONSTANT + 32*4) ||
           (method >= NV097_SET_VERTEX_DATA_ARRAY_OFFSET && method < NV097_SET_VERTEX_DATA_ARRAY_OFFSET + 16*4) ||
           (method >= NV097_SET_VERTEX_DATA_ARRAY_FORMAT && method < NV097_SET_VERTEX_DATA_ARRAY_FORMAT + 16*4);
}

#endif

static uint32_t dma_word(uint32_t base, uint32_t offset, uint32_t limit)
{
    uint64_t phys = (uint64_t)base + offset;
    if ((phys & 3) || (offset & 3) || (uint64_t)offset + 3 > limit || phys + 4 > XBOX_CONTIG_SIZE)
        ngb_stop("invalid pushbuffer GET", offset);
#ifdef NGB_DIRECT3D
    // One aligned word fits its page. Look up the current mapping each time
    // so a remap or a command read from a render target takes effect at once.
    if (ngb_scene_active && phys >= 4096 && !ngb_target_pages[phys >> 12]) {
        const uint8_t *page = ngb_contiguous_pages[phys >> 12];
        if (page) {
            uint32_t word;
            memcpy(&word, page + (phys & 4095), sizeof(word));
            return word;
        }
    }
#endif
    const void *ptr = phys < 4096 ? (void *)ngb_guest_pointer(XBOX_CONTIG_BASE + phys, 4) :
                                    dma_commands(phys, 4);
    if (!ptr) ngb_stop("unmapped DMA command", (uint32_t)phys);
    uint32_t word;
    memcpy(&word, ptr, 4);
    return word;
}

/* Direct-hit RAMHT lookup; never substitute a different handle or channel. */
static uint32_t object_instance(uint32_t handle, int binding)
{
    unsigned size_bits = (ramht & NV_PFIFO_RAMHT_SIZE) >> 16;
    unsigned bits = size_bits + 11;
    uint32_t channel = fifo_regs[NV_PFIFO_CACHE1_PUSH1 / 4] & 31;
    uint32_t hash = channel << (bits - 4);
    for (uint32_t h = handle; h; h >>= bits) hash ^= h & ((1u << bits) - 1);
    uint32_t base = (ramht & NV_PFIFO_RAMHT_BASE_ADDRESS) << 8;
    uint32_t entry[2];
    void *ptr = hash < (512u << size_bits) ?
        ngb_instance_aperture(NGB_PRAMIN_BASE + base + 8 * hash, sizeof(entry)) : NULL;
    if (!ptr) ngb_stop("unmapped RAMHT entry", handle);
    memcpy(entry, ptr, sizeof(entry));
    if (entry[0] != handle || !(entry[1] & NV_RAMHT_STATUS) ||
        (binding && (entry[1] & NV_RAMHT_ENGINE) != NV_RAMHT_ENGINE_GRAPHICS) ||
        ((entry[1] & NV_RAMHT_CHID) >> 24) != channel) ngb_stop("invalid RAMHT entry", handle);
    return (entry[1] & NV_RAMHT_INSTANCE) << 4;
}

static void dispatch_method(unsigned sub, uint32_t method, uint32_t value)
{
    if (method == NV_SET_OBJECT) {
        uint32_t instance = object_instance(value, 1), words[4];
        void *obj = ngb_instance_aperture(NGB_PRAMIN_BASE + instance, sizeof(words));
        if (!obj) ngb_stop("unmapped PGRAPH object", instance);
        memcpy(words, obj, sizeof(words));
        for (unsigned i = 0; i < 5; ++i)
            graph_regs[(NV_PGRAPH_CTX_CACHE1 + 32*i)/4 + sub] = i < 4 ? words[i] : instance;
        uint32_t *eng = &fifo_regs[NV_PFIFO_CACHE1_ENGINE / 4];
        *eng = (*eng & ~(3u << (4*sub))) | (1u << (4*sub));
        fifo_regs[NV_PFIFO_CACHE1_PULL1 / 4] = 1;
        char line[112];
        snprintf(line, sizeof(line), "PFIFO bind sub=%u handle=%08x instance=%08x class=%02x",
                 sub, value, instance, words[0] & 255u);
        ngb_kernel_log(line);
    }
    for (unsigned i = 0; i < 5; ++i)
        graph_regs[NV_PGRAPH_CTX_SWITCH1/4 + i] = graph_regs[(NV_PGRAPH_CTX_CACHE1 + 32*i)/4 + sub];
    if (method == NV_SET_OBJECT) return;
    if (method >= 0x180 && method < 0x200) value = object_instance(value, 0);
    ngb_pgraph_method(graph_regs, graph_regs[NV_PGRAPH_CTX_SWITCH1/4] & 255u, method, value);
}

#ifdef NGB_DIRECT3D
/* HLE has consumed these methods before the guest flushes its ring. Retire
 * adjacent, complete subchannel-zero state packets together. A flip, IRQ,
 * object switch, partial packet or jump goes through the regular parser. */
static unsigned state_packet_size(uint32_t header)
{
    if (header & ~(NV_PFIFO_CACHE1_DMA_STATE_METHOD | NV_PFIFO_CACHE1_DMA_STATE_METHOD_COUNT)) return 0;
    unsigned method = header & NV_PFIFO_CACHE1_DMA_STATE_METHOD;
    unsigned count = header >> 18;
    unsigned run = method == NV097_SET_TRANSFORM_CONSTANT_LOAD ? 1 : direct_state_words(method);
    return count && count <= run ? count + 1 : 0;
}

static unsigned retire_state_packets(uint32_t first, uint32_t base, uint32_t get, uint32_t put,
                                     uint32_t limit, uint32_t *state)
{
    unsigned words = state_packet_size(first);
    if (!words || !ngb_scene_active || put <= get) return 0;
    uint64_t physical = (uint64_t)base + get;
    if (physical < 4096 || physical >= XBOX_CONTIG_SIZE || (physical & 3)) return 0;
    unsigned page = physical >> 12, off = physical & 4095;
    const uint8_t *mapped = ngb_contiguous_pages[page];
    if (!mapped || ngb_target_pages[page]) return 0;
    unsigned available = 4096 - off;
    if (available > put - get) available = put - get;
    if (get > limit) return 0;
    if ((uint64_t)limit + 1 - get < available) available = limit + 1u - get;
    available /= 4;
    if (words > available) return 0;

    unsigned channel = fifo_regs[NV_PFIFO_CACHE1_PUSH1 / 4] & 31u;
    if (!(graph_regs[NV_PGRAPH_FIFO / 4] & 1) || !(fifo_regs[NV_PFIFO_CACHE1_PULL0 / 4] & 1) ||
        !(graph_regs[NV_PGRAPH_CTX_CONTROL / 4] & NV_PGRAPH_CTX_CONTROL_CHID) ||
        (graph_regs[NV_PGRAPH_CTX_USER / 4] & NV_PGRAPH_CTX_USER_CHID) != channel << 24 ||
        (graph_regs[NV_PGRAPH_CTX_CACHE1 / 4] & 255) != NV_KELVIN_PRIMITIVE) return 0;
    for (unsigned i = 0; i < 5; ++i)
        graph_regs[NV_PGRAPH_CTX_SWITCH1 / 4 + i] = graph_regs[NV_PGRAPH_CTX_CACHE1 / 4 + 8 * i];

    unsigned used = 0, packets = 0;
    uint32_t header = first;
    do {
        *state = ((header & NV_PFIFO_CACHE1_DMA_STATE_METHOD) + 4 * (words - 1)) & NV_PFIFO_CACHE1_DMA_STATE_METHOD;
        used += words;
        ++packets;
        if (used == available) break;
        memcpy(&header, mapped + off + used * 4, 4);
        words = state_packet_size(header);
    } while (words && words <= available - used);
    packet_count += packets;
    param_count += used - packets;
    direct_batched_words += used - packets;
    return used * 4;
}
#endif

static void execute_dma(uint32_t put)
{
    uint32_t *get = &fifo_regs[NV_PFIFO_CACHE1_DMA_GET / 4];
    if (*get == put) return;
    if (!(engines & NV_PMC_ENABLE_PFIFO) || !(fifo_regs[NV_PFIFO_CACHE1_PUSH0 / 4] & 1) ||
        !(fifo_regs[NV_PFIFO_CACHE1_DMA_PUSH / 4] & 1))
        ngb_stop("disabled NV2A DMA pusher", put);
    uint32_t slot = fifo_regs[NV_PFIFO_CACHE1_DMA_INSTANCE / 4] & 0xffff;
    uint32_t desc[3];
    void *instance = ngb_instance_aperture(NGB_PRAMIN_BASE + (slot << 4), sizeof(desc));
    if (!instance) ngb_stop("unmapped DMA instance", slot);
    memcpy(desc, instance, sizeof(desc));
    uint32_t base = (desc[2] & NV_DMA_ADDRESS) | (desc[0] >> 20);
    uint32_t cls = desc[0] & NV_DMA_CLASS;
    if ((cls != NV_DMA_FROM_MEMORY_CLASS && cls != NV_DMA_IN_MEMORY_CLASS) ||
        (desc[0] & NV_DMA_TARGET) != NV_DMA_TARGET_NVM)
        ngb_stop("unsupported pushbuffer DMA descriptor", desc[0]);
    if ((put & 3) || (uint64_t)put > (uint64_t)desc[1] + 1)
        ngb_stop("invalid pushbuffer PUT", put);

    unsigned jumps=0;
    while (*get != put) {
        uint32_t word = dma_word(base, *get, desc[1]);
        uint32_t *state = &fifo_regs[NV_PFIFO_CACHE1_DMA_STATE/4];
        uint32_t remaining = (*state & NV_PFIFO_CACHE1_DMA_STATE_METHOD_COUNT) >> 18;
        if (remaining) {
            uint32_t method = *state & NV_PFIFO_CACHE1_DMA_STATE_METHOD;
            unsigned sub = (*state & NV_PFIFO_CACHE1_DMA_STATE_SUBCHANNEL) >> 13;
            uint32_t chid = fifo_regs[NV_PFIFO_CACHE1_PUSH1/4] & 31;
            if (!(graph_regs[NV_PGRAPH_FIFO/4] & 1) || !(fifo_regs[NV_PFIFO_CACHE1_PULL0/4] & 1))
                ngb_stop("disabled graphics puller", *get);
            if (!(graph_regs[NV_PGRAPH_CTX_CONTROL/4] & NV_PGRAPH_CTX_CONTROL_CHID) ||
                (graph_regs[NV_PGRAPH_CTX_USER/4] & NV_PGRAPH_CTX_USER_CHID) != chid << 24) {
                graph_regs[NV_PGRAPH_TRAPPED_ADDR/4] = chid << 24;
                graph_regs[NV_PGRAPH_INTR/4] |= NV_PGRAPH_INTR_CONTEXT_SWITCH;
                if (!context_wait) trace("context interrupt", *get, chid);
                context_wait = 1;
                return;
            }
            int notify = method == NV097_NO_OPERATION && word &&
                (graph_regs[(NV_PGRAPH_CTX_CACHE1/4)+sub] & 255u) == NV_KELVIN_PRIMITIVE;
            if (notify) {
                graph_regs[NV_PGRAPH_TRAPPED_ADDR/4] = chid << 24 | sub << 16 | method;
                graph_regs[NV_PGRAPH_TRAPPED_DATA_LOW/4] = word;
                graph_regs[NV_PGRAPH_NSOURCE/4] = NV_PGRAPH_NSOURCE_NOTIFICATION;
                graph_regs[NV_PGRAPH_INTR/4] |= NV_PGRAPH_INTR_ERROR;
            } else if (method == NV097_FLIP_STALL && (graph_regs[NV_PGRAPH_CTX_CACHE1/4+sub] & 255) == 0x97)
                flip_wait = !flip_ready();
            else dispatch_method(sub, method, word);
            unsigned consumed = 1;
            int increment = !(*state & 1);
            int vertices = method == NV097_ARRAY_ELEMENT16 || method == NV097_ARRAY_ELEMENT32 ||
                           method == NV097_INLINE_ARRAY;
#ifdef NGB_DIRECT3D
            unsigned run = direct_state_words(method + (increment ? 4 : 0));
            int batch = run || (!increment && vertices);
#else
            int batch = increment ? batch_state_method(method + 4) : vertices;
#endif
            if (ngb_scene_active && batch && !sub && remaining > 1 && !notify && !flip_wait &&
                (graph_regs[NV_PGRAPH_CTX_SWITCH1/4] & 255u) == NV_KELVIN_PRIMITIVE) {
                uint64_t available = (uint64_t)desc[1] + 1 - *get;
                if (put > *get && available > put - *get) available = put - *get;
                unsigned count = available / 4 < remaining ? (unsigned)(available / 4) : remaining;
#ifdef NGB_DIRECT3D
                if (increment && count > run + 1) count = run + 1;
#endif
                uint64_t address = (uint64_t)base + *get;
                if (count > 1 && address >= 4096 && address + count * 4 <= XBOX_CONTIG_SIZE) {
                    uint32_t *words = dma_commands(address + 4, (count - 1) * 4);
                    if (words) {
#ifdef NGB_DIRECT3D
                        consumed = count;
                        direct_batched_words += count - 1;
#else
                        if (increment) {
                            consumed += ngb_scene_submit_state(method + 4, words, count - 1);
                        } else {
                            ngb_scene_submit_vertices(method, words, count - 1);
                            consumed = count;
                        }
#endif
                    }
                }
            }
            if (increment) method = (method + consumed * 4) & NV_PFIFO_CACHE1_DMA_STATE_METHOD;
            *state = (*state & ~(NV_PFIFO_CACHE1_DMA_STATE_METHOD | NV_PFIFO_CACHE1_DMA_STATE_METHOD_COUNT)) |
                     method | ((remaining-consumed) << 18);
            param_count += consumed;
            *get += 4 * consumed;
            if (notify) { context_wait = 1; return; }
            if (flip_wait) return;
            continue;
        }
#ifdef NGB_DIRECT3D
        unsigned retired = retire_state_packets(word, base, *get, put, desc[1], state);
        if (retired) {
            *get += retired;
            continue;
        }
#endif
        uint32_t type = word & 0xe0030003u;
        if (type == 0 || type == 0x40000000u) {
            *state = (word & (NV_PFIFO_CACHE1_DMA_STATE_METHOD | NV_PFIFO_CACHE1_DMA_STATE_SUBCHANNEL |
                              NV_PFIFO_CACHE1_DMA_STATE_METHOD_COUNT)) | (type != 0);
            ++packet_count;
            *get += 4;
            continue;
        }
        if ((word & 3) != 1 && (word & 0xe0000003u) != 0x20000000u)
            ngb_stop("unhandled pushbuffer command", word);
        uint32_t target = (word & 3) == 1 ? word & ~3u : word & 0x1fffffffu;
        if ((uint64_t)target > (uint64_t)desc[1] + 1)
            ngb_stop("invalid pushbuffer jump target", target);
        if (++jumps>4096) ngb_stop("cyclic pushbuffer jump chain",*get);
        trace("DMA jump", *get, target);
        fifo_regs[NV_PFIFO_CACHE1_DMA_GET_JMP_SHADOW / 4] = *get + 4;
        *get = target;
    }
    if ((packet_count || param_count) && ngb_mmio_trace_enabled()) {
        char line[128];
        snprintf(line, sizeof(line), "PFIFO executed start=%08x GET=PUT=%08x packets=%u arguments=%u", batch_first, put, packet_count, param_count);
        ngb_kernel_log(line);
    }
}

/* Materialize GPU writes before returning control to guest code, including
 * FIFO stalls and context-switch interrupts. */

uint64_t ngb_fifo_time_ns(void)
{
    return fifo_ns + (fifo_start ? ngb_elapsed_ns() - fifo_start : 0);
}

static void submit_dma(uint32_t put)
{
    if (put != fifo_regs[NV_PFIFO_CACHE1_DMA_GET/4]) {
        fifo_start = ngb_elapsed_ns();
        execute_dma(put);
        fifo_ns += ngb_elapsed_ns() - fifo_start;
        fifo_start = 0;
    } else {
        execute_dma(put);
    }
    ngb_menu_gpu_flush();
}

#ifdef NGB_DIRECT3D
static void service_dma(void)
{
    if (servicing_dma || context_wait || flip_wait) return;
    servicing_dma = true;
    ngb_direct_check_render_error();
    uint64_t gate = atomic_load(&render_gate);
    uint32_t actual = fifo_regs[NV_PFIFO_CACHE1_DMA_PUT/4];
    uint32_t limit = (gate >> 32) ? (uint32_t)gate : actual;
    if (fifo_regs[NV_PFIFO_CACHE1_DMA_GET/4] != limit) {
        // An interrupt check can drain deferred GPU work before delivering
        // an IRQ. Keep that submission outside any prepared draw scope.
        unsigned owner = ngb_d3d_model_suspend();
        submit_dma(limit);
        ngb_d3d_model_resume(owner);
    }
    deferred_dma = fifo_regs[NV_PFIFO_CACHE1_DMA_GET/4] != actual;
    servicing_dma = false;
}
#endif

static void resume_dma(void)
{
#ifdef NGB_DIRECT3D
    if (atomic_load(&render_gate) >> 32) { service_dma(); return; }
#endif
    submit_dma(fifo_regs[NV_PFIFO_CACHE1_DMA_PUT/4]);
}

void ngb_nv2a_write8(uint32_t va, uint8_t value)
{
    if (va == 0xfd6813c8u) { palette_component = 3u*value; return; }
    if (va == 0xfd6813c9u) {
        palette[palette_component/3][palette_component%3] = value;
        palette_component = (palette_component+1) % (256*3);
        return;
    }
    if (va == CRTC_INDEX) crtc_index = value;
    else if (va == CRTC_DATA) crtc_regs[crtc_index] = value;
    else ngb_stop("unsupported NV2A byte write", va);
    trace("write8", va, value);
}

uint8_t ngb_nv2a_read8(uint32_t va)
{
    uint8_t value;
    if (va == CRTC_INDEX) value = crtc_index;
    else if (va == CRTC_DATA) value = crtc_regs[crtc_index];
    else if (va == 0xfd003214u || va == 0xfd002400u || va == 0xfd003220u)
        return (uint8_t)ngb_nv2a_read32(va);
    else value = (uint8_t)(pll_coeff(va & ~3u) >> (8 * (va & 3u)));
    trace("read8", va, value);
    return value;
}

uint32_t ngb_nv2a_read32(uint32_t va)
{
    uint32_t value;
    if (va >= 0xfd800000u && va < 0xfda00000u) {
#ifdef NGB_DIRECT3D
        if (nv2a_user_read_hook) nv2a_user_read_hook();
        if (deferred_dma) service_dma();
#endif
        value = fifo_regs[user_register(va) / 4];
        trace("USER read", va, value);
        return value;
    }
    void *instance = ngb_instance_aperture(va, sizeof(value));
    if (instance) {
        memcpy(&value, instance, sizeof(value));
        return value;
    }
    uint32_t *reg = setup_register(va);
    if (reg) {
        trace("read", va, *reg);
        return *reg;
    }
    switch (va) {
    case 0xfd008100u: value = video_regs[0x100/4]; break;
    case 0xfd40071cu: value = 0; break;
    case 0xfd600800u: value = scanout_start; break;
    case 0xfd003214u:
        value = fifo_regs[NV_PFIFO_CACHE1_PUT / 4] == fifo_regs[NV_PFIFO_CACHE1_GET / 4]
              ? NV_PFIFO_CACHE1_STATUS_LOW_MARK : 0; break;
    case 0xfd002400u: value = NV_PFIFO_RUNOUT_STATUS_LOW_MARK; break; /* No overflow queued. */
    case 0xfd100410u: value = 0; break; /* Coherent boot memory: no writeback pending. */
    case 0xfd400700u: value = 0; break; /* Idle: no PGRAPH work has been accepted. */
    case 0xfd400100u: value = graph_regs[NV_PGRAPH_INTR / 4]; break;
    case 0xfd002100u: value = fifo_regs[NV_PFIFO_INTR_0 / 4]; break;
    case 0xfd400750u: value = rdi_index; break;
    case 0xfd400754u: value = *next_rdi_word(); break;
    case FIFO_RAMHT: value = ramht; break;
    case FIFO_RAMFC: value = ramfc; break;
    case FB_NVM: value = fb_nvm; break;
    case ENGINE_ENABLE: value = engines; break;
    case CORE_PLL: case MEMORY_PLL: case VIDEO_PLL: value = pll_coeff(va); break;
    case TIMER_NUM: value = timer_num; break;
    case TIMER_DEN: value = timer_den; break;
    case TIMER_ALARM: value = alarm_low; break;
    case TIMER_LOW: value = (uint32_t)(timer_ticks(ngb_elapsed_ns()) << 5); break;
    case TIMER_HIGH: value = (timer_ticks(ngb_elapsed_ns()) >> 27) & 0x1fffffffu; break;
    case TIMER_STATUS: sample_alarm(); value = timer_status; break;
    /* The desktop bootstrap leaves these PFB configuration words and PBUS debug bits clear. */
    case FB_CONFIG0: case FB_CONFIG1: case BUS_DEBUG: value = 0; break;
    case MASTER_STATUS: sample_vblank(); value = master_status(); break;
    case MASTER_IRQ: value = master_irq; break;
    case CRTC_STATUS: sample_vblank(); value = crtc_status; break;
    case PCI_LATENCY: value = pci_latency; break;
    case PCI_ROM: value = 0; break; /* No expansion ROM on the integrated device. */
    case PCI_AGP_COMMAND: value = agp_command; break;
    case PCI_ID: value = 0x02a010de; break;
    case PCI_COMMAND: value = command; break;
    case PCI_CLASS_REV: value = 0x030000a1; break;
    case TIMER_IRQ: value = timer_irq; break;
    case CRTC_IRQ: value = crtc_irq; break;
    case MEMORY_SIZE: value = XBOX_CONTIG_SIZE; break;
    default: ngb_stop("unsupported NV2A read", va);
    }
    trace("read", va, value);
    return value;
}

void ngb_nv2a_write32(uint32_t va, uint32_t value)
{
    if (va >= 0xfd800000u && va < 0xfda00000u) {
        uint32_t reg = user_register(va);
        trace("USER write", va, value);
        if (reg == NV_PFIFO_CACHE1_DMA_PUT) {
            fifo_regs[reg/4] = value;
#ifdef NGB_DIRECT3D
            atomic_store(&guest_put, value);
            if (atomic_load(&render_gate) >> 32) {
                deferred_dma = true;
                service_dma();
                return;
            }
#endif
            if (context_wait || flip_wait) return;
            {
                batch_first = fifo_regs[NV_PFIFO_CACHE1_DMA_GET/4];
                packet_count = param_count = 0;
            }
            submit_dma(value);
        }
        else fifo_regs[reg / 4] = value;
        return;
    }
    void *instance = ngb_instance_aperture(va, sizeof(value));
    if (instance) {
        memcpy(instance, &value, sizeof(value));
        if (va == NGB_PRAMIN_BASE + NGB_INSTANCE_PADDING || !ngb_instance_aperture(va + 4, 1))
            trace("PRAMIN write", va, value);
        return;
    }
    uint32_t *reg = setup_register(va);
    if (reg) {
        if (va == 0xfd003240u && value != fifo_regs[NV_PFIFO_CACHE1_DMA_GET / 4])
            ngb_stop("NV2A FIFO DMA submission", value);
        *reg = value;
        trace("write", va, value);
        if (va == 0xfd400720u && (value & 1) && flip_wait && flip_ready()) {
            flip_wait = 0;
            resume_dma();
        }
        if (va == 0xfd400720u && (value & 1) && context_wait &&
            !(graph_regs[NV_PGRAPH_INTR/4] & (NV_PGRAPH_INTR_CONTEXT_SWITCH | NV_PGRAPH_INTR_ERROR))) {
            context_wait = 0;
            resume_dma();
        }
        return;
    }
    switch (va) {
    case 0xfd600800u: {
        uint32_t address = value & 0x07fffffcu;
        if (address != scanout_start) ngb_pad_flip();
        scanout_start = address;
        break;
    }
    case 0xfd008100u: video_regs[0x100/4] &= ~value; break;
    case 0xfd40071cu:
        if (value & ~NV_PGRAPH_INCREMENT_READ_3D) ngb_stop("unsupported PGRAPH increment", value);
        if (value) {
            uint32_t surface = graph_regs[NV_PGRAPH_SURFACE/4];
            unsigned mod = (surface & NV_PGRAPH_SURFACE_MODULO_3D) >> 28;
            if (!mod) ngb_stop("invalid flip modulo", surface);
            unsigned next = (((surface & NV_PGRAPH_SURFACE_READ_3D) >> 24) + 1) % mod;
            graph_regs[NV_PGRAPH_SURFACE/4] = (surface & ~NV_PGRAPH_SURFACE_READ_3D) | (next << 24);
            if (flip_wait && flip_ready() && (graph_regs[NV_PGRAPH_FIFO/4] & 1)) {
                flip_wait = 0;
                resume_dma();
            }
        }
        break;
    case 0xfd400788u: {
        if (value != 1) ngb_stop("unsupported graphics context transfer", value);
        uint32_t inst = (graph_regs[NV_PGRAPH_CHANNEL_CTX_POINTER/4] & 0xffff) << 4;
        void *obj = ngb_instance_aperture(NGB_PRAMIN_BASE + inst, 4);
        if (!obj) ngb_stop("unmapped graphics context", inst);
        memcpy(&graph_regs[NV_PGRAPH_CTX_USER/4], obj, 4);
        break;
    }
    case 0xfd400100u:
        graph_regs[NV_PGRAPH_INTR/4] &= ~value;
        if (value & NV_PGRAPH_INTR_ERROR) graph_regs[NV_PGRAPH_NSOURCE/4] = 0;
        break;
    case 0xfd002100u: fifo_regs[NV_PFIFO_INTR_0 / 4] &= ~value; break;
    case 0xfd400750u: rdi_index = value; break;
    case 0xfd400754u: *next_rdi_word() = value; break;
    case 0xfd100410u:
        if (value & ~NV_PFB_WBC_FLUSH) ngb_stop("unsupported PFB writeback command", value);
        atomic_thread_fence(memory_order_seq_cst);
        break;
    case FIFO_RAMHT: ramht = value; break;
    case FIFO_RAMFC: ramfc = value; break;
    case FB_NVM: fb_nvm = value; break;
    case ENGINE_ENABLE: {
        uint32_t changed = engines ^ (value & ENGINE_MASK);
        engines = value & ENGINE_MASK;
        if ((changed & NV_PMC_ENABLE_PFIFO) && !(engines & NV_PMC_ENABLE_PFIFO)) {
            ramht = ramfc = 0;
            memset(fifo_regs, 0, sizeof(fifo_regs));
        }
        if ((changed & NV_PMC_ENABLE_PGRAPH) && !(engines & NV_PMC_ENABLE_PGRAPH)) reset_graph();
        if (changed & ENGINE_CRTC) {
            crtc_status = crtc_irq = 0;
            frame = ngb_elapsed_ns() / 16666667u;
        }
        if (changed & ENGINE_TIMER) {
            reset_timer();
            timer_epoch = ngb_elapsed_ns();
        }
        break;
    }
    case TIMER_NUM: case TIMER_DEN: {
        sample_alarm();
        uint64_t now = ngb_elapsed_ns();
        timer_base = timer_ticks(now);
        timer_epoch = now;
        if (va == TIMER_NUM) timer_num = value;
        else timer_den = value;
        break;
    }
    case TIMER_LOW: case TIMER_HIGH: {
        sample_alarm();
        uint64_t now = ngb_elapsed_ns();
        uint64_t ticks = timer_ticks(now);
        const uint64_t low_mask = (1ull << 27) - 1;
        if (va == TIMER_LOW) timer_base = (ticks & ~low_mask) | (value >> 5);
        else timer_base = ((uint64_t)(value & 0x1fffffffu) << 27) | (ticks & low_mask);
        timer_epoch = now;
        alarm_tick = next_alarm(timer_base);
        break;
    }
    case TIMER_ALARM:
        alarm_low = value & 0xffffffe0u;
        alarm_tick = next_alarm(timer_ticks(ngb_elapsed_ns()));
        break;
    case TIMER_STATUS: sample_alarm(); timer_status &= ~value; break;
    case MASTER_IRQ: master_irq = value; break;
    case CRTC_STATUS: sample_vblank(); crtc_status &= ~value; break;
    case PCI_LATENCY: pci_latency = value & 0xff00u; break;
    case PCI_ROM: if (value) ngb_stop("unsupported NV2A expansion ROM", value); break;
    case PCI_AGP_COMMAND: agp_command = value; break;
    case PCI_COMMAND: command = value; break;
    case TIMER_IRQ:
        sample_alarm();
        timer_irq = value & NV_PTIMER_INTR_0_ALARM;
        break;
    case CRTC_IRQ: crtc_irq = value; break;
    default: ngb_stop("unsupported NV2A write", va);
    }
    trace("write", va, value);
}
