#include "audio_boot.h"
#include "runtime.h"
#include "apu/apu_regs.h"
#include <string.h>
#include <math.h>

static uint8_t ac97[4096];
static int reported_voice, voice_engine_paused;
static uint64_t last_audio_frame, last_idle_scan_frame, active_voices[4];
static double fractional_samples[256];
static uint32_t hrir[HRTF_ENTRY_COUNT][16];
static uint8_t locked[256];
static uint32_t voice_setup[0x1900 / 4];
static uint32_t dsp_words[2][0x10000 / 4];
static uint32_t apu_config[0x5000 / 4];

#include "audio_output.inc"
#include "voice_pcm.inc"

void ngb_audio_reset(void)
{
    init_levels();ngb_pcm_flush(0);ngb_pcm_flush(1);
    reported_voice = voice_engine_paused = 0;
    last_audio_frame = 0;
    last_idle_scan_frame = UINT64_MAX;
    memset(mix_params,0,sizeof mix_params);
    memset(active_voices, 0, sizeof(active_voices));
    memset(fractional_samples, 0, sizeof(fractional_samples));
    memset(ac97, 0, sizeof(ac97));
    memset(hrir, 0, sizeof(hrir));
    memset(locked, 0, sizeof(locked));
    memset(voice_setup, 0, sizeof(voice_setup));
    memset(dsp_words, 0, sizeof(dsp_words));
    memset(apu_config, 0, sizeof(apu_config));
    for (unsigned i=0; i<9; ++i) apu_config[NV_PAPU_TVL2D/4+i]=0xffff;
}

uint32_t ngb_audio_irq(unsigned line)
{
    if (line == 6)
        return ac97[0x130] & 0x51;
    uint32_t enable = apu_config[NV_PAPU_IEN / 4];
    return (enable & 1) ? (enable & apu_config[NV_PAPU_ISTS / 4] & ~1u) : 0;
}

uint32_t ngb_ac97_read(uint32_t va, unsigned size)
{
    unsigned off = va - 0xfec00000u;
    uint32_t v = 0;
    if ((size != 1 && size != 2 && size != 4) || off > sizeof(ac97) - size)
        ngb_stop("invalid AC97 read", va);
    memcpy(&v, ac97 + off, size);
    return v;
}
void ngb_ac97_write(uint32_t va, unsigned size, uint32_t value)
{
    unsigned off = va - 0xfec00000u;
    if ((size != 1 && size != 2 && size != 4) || off > sizeof(ac97) - size)
        ngb_stop("invalid AC97 write", va);
    if (off == 0x12c && size == 4) {
        ac97[0x131] = (value & 2) ? 1 : 0;
        ngb_kernel_log((value & 2) ? "AC97 codec ready" : "AC97 codec in reset");
    }
    if (off == 0x130 && size == 4)
        return; /* primary-ready bit is read only */
    if (off >= 0x100 && off < 0x180 && (off & 15) == 11)
        value &= ~2u;
    memcpy(ac97 + off, &value, size);
}

static uint32_t *apu_latch(uint32_t offset)
{
    /* The main PAPU register file is separate from the voice method FIFO and
     * DSP apertures. Status, sample time and guest-memory writes have dedicated
     * handlers, as in mcpx_apu_read/write in the desktop runtime. */
    if (!(offset & 3) && ((offset >> 16) == 3 || (offset >> 16) == 5))
        return &dsp_words[(offset >> 16) == 5][(offset & 65535) / 4];
    if ((offset & 3) || offset < 0x1000 || offset >= sizeof(apu_config))
        ngb_stop("unsupported APU register", offset);
    return &apu_config[offset / 4];
}

uint32_t ngb_apu_read(uint32_t va)
{
    /* The USB driver compares frame time with the MCPX APU global sample
     * counter. Model the 48 kHz clock during silent bootstrap. */
    if (va == 0xfe80200cu)
        return (uint32_t)(ngb_elapsed_ns() * 48 / 1000000);
    if (va == 0xfe820010u)
        return 0x80; /* synchronous voice method FIFO */
    if (va == 0xfe800000u + NV_PAPU_ISTS)
        return (apu_config[NV_PAPU_ISTS / 4] & ~NV_PAPU_ISTS_GINTSTS) |
               (ngb_audio_irq(5) ? NV_PAPU_ISTS_GINTSTS : 0);
    return *apu_latch(va - 0xfe800000u);
}

static uint32_t *voice_record(unsigned voice)
{
    uint64_t address = (uint64_t)apu_config[NV_PAPU_VPVADDR / 4] + voice * NV_PAVS_SIZE;
    if (voice >= 256 || address >= 0x08000000 || (address & 3))
        ngb_stop("invalid APU voice table", voice);
    return ngb_dma_pointer((uint32_t)address, NV_PAVS_SIZE);
}

static void finish_buffer_voice(unsigned id, uint32_t *v)
{
    uint64_t address = (uint64_t)apu_config[NV_PAPU_FENADDR / 4] + 16u *
        (MCPX_HW_NOTIFIER_BASE_OFFSET + id * MCPX_HW_NOTIFIER_COUNT + MCPX_HW_NOTIFIER_SSLA_DONE) + 14;
    if (address + 2 > 0x08000000) ngb_stop("invalid voice notifier", id);
    uint8_t *notify = ngb_dma_pointer((uint32_t)address, 2);
    v[NV_PAVS_VOICE_PAR_STATE / 4] &= ~NV_PAVS_VOICE_PAR_STATE_ACTIVE_VOICE;
    active_voices[id/64] &= ~(UINT64_C(1) << (id%64));
    last_idle_scan_frame = UINT64_MAX;
    notify[0] = 1;
    notify[1] = NV1BA0_NOTIFICATION_STATUS_DONE_SUCCESS;
    apu_config[NV_PAPU_ISTS / 4] |= NV_PAPU_ISTS_FEVINTSTS | NV_PAPU_ISTS_FENINTSTS;
}

/* Mix from the same play cursor and fractional pitch used by guest notifications. */
static void advance_buffer_voices(void)
{
    uint64_t frame = ngb_elapsed_ns() * 48 / 1000000 / 32;
    uint64_t samples = (frame - last_audio_frame) * 32;
    if (!samples) return;
    last_audio_frame = frame;
    if (voice_engine_paused) return;
    unsigned n=samples>MIX_LIMIT?MIX_LIMIT:(unsigned)samples;
    if(!(active_voices[0]|active_voices[1]|active_voices[2]|active_voices[3])){
        ngb_pcm_submit(0,NULL,n);return;
    }
    memset(pcm_mix,0,n*sizeof(*pcm_mix));
    for (unsigned group = 0; group < 4; ++group) {
        uint64_t handles = active_voices[group];
        while (handles) {
            unsigned bit = __builtin_ctzll(handles), id = group * 64 + bit;
            handles &= handles - 1;
            uint32_t *v = voice_record(id);
            uint32_t state = v[NV_PAVS_VOICE_PAR_STATE / 4];
            if (!(state & NV_PAVS_VOICE_PAR_STATE_ACTIVE_VOICE)) {
                active_voices[group] &= ~(UINT64_C(1) << bit);
                continue;
            }
            uint32_t fmt = v[NV_PAVS_VOICE_CFG_FMT / 4];
            if (locked[id] || (state & NV_PAVS_VOICE_PAR_STATE_PAUSED) ||
                (fmt & NV_PAVS_VOICE_CFG_FMT_DATA_TYPE))
                continue;
            uint32_t end = v[NV_PAVS_VOICE_PAR_NEXT / 4] & NV_PAVS_VOICE_PAR_NEXT_EBO;
            uint32_t loop = v[NV_PAVS_VOICE_CUR_PSH_SAMPLE / 4] & NV_PAVS_VOICE_CUR_PSH_SAMPLE_LBO;
            if ((fmt & NV_PAVS_VOICE_CFG_FMT_LOOP) && loop > end) continue;
            int16_t pitch = (int16_t)(v[NV_PAVS_VOICE_TAR_PITCH_LINK / 4] >> 16);
            double rate=playback_rate(id,pitch);
            mix_voice(id,v,fmt,v[NV_PAVS_VOICE_PAR_OFFSET/4]&0xffffff,end,loop,fractional_samples[id],rate,n,samples-n);
            double step = fractional_samples[id] + samples * rate;
            uint64_t advance = (uint64_t)step;
            fractional_samples[id] = step - advance;
            uint32_t *offset = &v[NV_PAVS_VOICE_PAR_OFFSET / 4];
            uint64_t pos = (*offset & NV_PAVS_VOICE_PAR_OFFSET_CBO) + advance;
            if (pos > end) {
                if (fmt & NV_PAVS_VOICE_CFG_FMT_LOOP)
                    pos = loop + (pos - end - 1) % (end - loop + 1);
                else {
                    pos = end;
                    finish_buffer_voice(id, v);
                }
            }
            *offset = (*offset & ~NV_PAVS_VOICE_PAR_OFFSET_CBO) | (uint32_t)pos;
        }
    }
    submit_mix(n);
}

static void start_voice(uint32_t arg)
{
    advance_buffer_voices();
    unsigned handle = arg & 0xffff;
    uint32_t *v = voice_record(handle);
    active_voices[handle/64] |= UINT64_C(1) << (handle%64);
    fractional_samples[handle] = 0;
    uint32_t antecedent = apu_config[NV_PAPU_FEAV / 4];
    unsigned list = (antecedent >> 16) & 3;
    uint32_t *link = list ? &apu_config[(NV_PAPU_TVL2D + 12 * (list - 1)) / 4]
                          : &voice_record(antecedent & 65535)[NV_PAVS_VOICE_TAR_PITCH_LINK / 4];
    v[NV_PAVS_VOICE_TAR_PITCH_LINK / 4] =
        (v[NV_PAVS_VOICE_TAR_PITCH_LINK / 4] & 0xffff0000) | (*link & 65535);
    *link = (*link & 0xffff0000) | handle;
    v[NV_PAVS_VOICE_PAR_OFFSET / 4] &= ~NV_PAVS_VOICE_PAR_OFFSET_CBO;
    uint32_t *state = &v[NV_PAVS_VOICE_PAR_STATE / 4];
    *state = (*state & 0x00ffffff) | (arg & 0xff000000) | NV_PAVS_VOICE_PAR_STATE_ACTIVE_VOICE;
    for (unsigned i = 0; i < 2; i++) {
        unsigned stage = (arg >> (28 - 4 * i)) & 15;
        if (stage < 1 || stage > 3)
            continue;
        unsigned envelope = NV_PAVS_VOICE_CFG_ENV0 + 8 * i + (stage == 3 ? 4 : 0);
        uint32_t ticks = stage == 2 ? 0 : ((v[envelope / 4] >> 12) & 4095) * 16;
        uint32_t *count = &v[NV_PAVS_VOICE_CUR_ECNT / 4];
        *count = (*count & ~(0xffffu << (16 * i))) | (ticks << (16 * i));
    }
    if (!reported_voice) {
        ngb_kernel_log("APU voice activated in guest RAM");
        reported_voice = 1;
    }
}

static int voice_method(uint32_t method, uint32_t value)
{
    /* DirectSound pauses the voice engine while relinking its lists, then
     * requests a completion in global notifier slot zero before editing RAM. */
    if (method == 0x10c && value <= 1) {
        advance_buffer_voices();
        voice_engine_paused = !value;
        return 1;
    }
    if (method == 0x104 && value == 2) {
        uint32_t address = apu_config[NV_PAPU_FENADDR/4];
        if (address >= 0x08000000u-15) ngb_stop("invalid APU notifier table",address);
        uint8_t *notify = ngb_dma_pointer(address+14,2);
        notify[0] = 1;
        notify[1] = NV1BA0_NOTIFICATION_STATUS_DONE_SUCCESS;
        return 1;
    }
    if (method == NV1BA0_PIO_SET_ANTECEDENT_VOICE) {
        apu_config[NV_PAPU_FEAV / 4] = value;
        return 1;
    }
    if (method == NV1BA0_PIO_VOICE_OFF) {
        unsigned id = value & NV1BA0_PIO_VOICE_OFF_HANDLE;
        uint32_t *v = voice_record(id);
        if (v[NV_PAVS_VOICE_CFG_FMT / 4] & NV_PAVS_VOICE_CFG_FMT_DATA_TYPE)
            ngb_stop("unsupported stream voice notification", id);
        advance_buffer_voices();
        finish_buffer_voice(id, v);
        return 1;
    }
    if (method == NV1BA0_PIO_VOICE_PAUSE) {
        advance_buffer_voices();
        uint32_t *state = &voice_record(value & 65535)[NV_PAVS_VOICE_PAR_STATE / 4];
        *state = (*state & ~NV_PAVS_VOICE_PAR_STATE_PAUSED) | (value & NV1BA0_PIO_VOICE_PAUSE_ACTION);
        return 1;
    }
    if (method == NV1BA0_PIO_VOICE_ON) {
        start_voice(value);
        return 1;
    }
    if (method == NV1BA0_PIO_SET_CURRENT_VOICE) {
        if (value >= 256)
            ngb_stop("invalid APU voice", value);
        apu_config[NV_PAPU_FECV / 4] = value;
        return 1;
    }
    unsigned voice = apu_config[NV_PAPU_FECV / 4];
    if (voice >= 256)
        ngb_stop("invalid current APU voice", voice);
    if (method == NV1BA0_PIO_VOICE_LOCK) {
        advance_buffer_voices();
        locked[voice] = value & 1;
        return 1;
    }
    if (method == NV1BA0_PIO_SET_CURRENT_HRTF_ENTRY) {
        if (value >= HRTF_ENTRY_COUNT)
            ngb_stop("invalid HRTF entry", value);
        return 1;
    }
    if (method >= NV1BA0_PIO_SET_HRIR && method <= NV1BA0_PIO_SET_HRIR_X) {
        hrir[voice_setup[NV1BA0_PIO_SET_CURRENT_HRTF_ENTRY / 4]][(method - 0x400) / 4] = value;
        return 1;
    }
    uint32_t mask;
    if ((method >= 0x300 && method <= 0x318) || (method >= 0x360 && method <= 0x36c) || method == 0x350 ||
        method == 0x370 || method == 0x374 || method == 0x378)
        mask = UINT32_MAX;
    else if (method == 0x31c)
        mask = 0xffff;
    else if (method == 0x37c)
        mask = 0xffff0000;
    else if (method == 0x3a0 || method == 0x3a4 || method == 0x3d8 || method == 0x3dc)
        mask = 0xffffff;
    else
        return 0;
    uint64_t address = (uint64_t)apu_config[NV_PAPU_VPVADDR / 4] + voice * NV_PAVS_SIZE + (method & 127);
    if (address >= 0x08000000 || (address & 3))
        ngb_stop("invalid APU voice table", voice);
    uint32_t *word = ngb_dma_pointer((uint32_t)address, 4);
    *word = (*word & ~mask) | (value & mask);
    return 1;
}

void ngb_apu_write(uint32_t va, uint32_t value)
{
    if (va - 0xfe820000u < 0x10000) {
        uint32_t m = va - 0xfe820000u;
        if ((m & 3) || m >= sizeof(voice_setup))
            ngb_stop("unsupported APU method", m);
        if (m == NV1BA0_PIO_SET_CURRENT_INBUF_SGE_OFFSET || m == NV1BA0_PIO_SET_CURRENT_OUTBUF_SGE_OFFSET) {
            uint32_t handle = voice_setup[(m == 0x808 ? 0x804 : 0x1800) / 4];
            uint64_t slot = (uint64_t)apu_config[NV_PAPU_VPSGEADDR / 4] + (uint64_t)handle * 8;
            if (slot >= 0x08000000)
                ngb_stop("invalid APU SGE", handle);
            uint32_t page = value & 0xfffff000u;
            memcpy(ngb_dma_pointer((uint32_t)slot, 4), &page, 4);
        } else if (!voice_method(m, value) &&
                   !(m == 0x804 || m == 0x1800 || (m >= 0x200 && m <= 0x280) || (m >= 0x2a0 && m <= 0x2b0) ||
                     m == 0x2c0 || (m >= 0x1000 && m < 0x1020)))
            ngb_stop("unsupported APU method", m);
        if ((apu_config[NV_PAPU_FECTL/4] & NV_PAPU_FECTL_FEMETHMODE) != NV_PAPU_FECTL_FEMETHMODE_TRAPPED) {
            apu_config[NV_PAPU_FEDECMETH / 4] = m;
            apu_config[NV_PAPU_FEDECPARAM / 4] = value;
        }
        if(m>=0x200 && m<=0x224 && ((voice_setup[m/4]^value)&7))gain_generation++;
        voice_setup[m / 4] = value;
        return;
    }
    if (va - 0xfe800000u < 0x80000) {
        uint32_t reg = va - 0xfe800000u;
        uint32_t *word = apu_latch(reg);
        if (reg == NV_PAPU_ISTS)
            *word &= ~value;
        else {
            if (reg == NV_PAPU_FEMEMDATA)
                memcpy(ngb_dma_pointer(apu_config[NV_PAPU_FEMEMADDR / 4], 4), &value, 4);
            *word = value;
        }
        return;
    }
}

/* A finished voice stays on its guest-owned list until DirectSound unlinks
 * it in the SE2FE_IDLE_VOICE trap handler. Report a single method at a time
 * and keep its parameters latched until the guest resumes the front end. */
static void report_idle_voice(void)
{
    uint32_t control=apu_config[NV_PAPU_FECTL/4];
    if (last_idle_scan_frame == last_audio_frame || voice_engine_paused ||
        (apu_config[NV_PAPU_ISTS/4] & NV_PAPU_ISTS_FETINTSTS) ||
        (control & NV_PAPU_FECTL_FEMETHMODE) ||
        !(apu_config[NV_PAPU_FETFORCE1/4] & NV_PAPU_FETFORCE1_SE2FE_IDLE_VOICE)) return;
    /* The list and ACTIVE bit live in guest memory. Recheck them each APU
     * frame, including after an acknowledged trap whose voice is still linked. */
    last_idle_scan_frame = last_audio_frame;
    for (unsigned list=0; list<3; ++list) {
        uint32_t *regs=&apu_config[NV_PAPU_TVL2D/4+3*list];
        unsigned id=regs[0]&65535;
        for (unsigned n=0; id<256 && n<256; ++n) {
            uint32_t *v=voice_record(id);
            unsigned next=v[NV_PAVS_VOICE_TAR_PITCH_LINK/4]&65535;
            if (!(v[NV_PAVS_VOICE_PAR_STATE/4] & NV_PAVS_VOICE_PAR_STATE_ACTIVE_VOICE)) {
                regs[1]=id; regs[2]=next;
                apu_config[NV_PAPU_FEDECMETH/4]=SE2FE_IDLE_VOICE;
                apu_config[NV_PAPU_FEDECPARAM/4]=id;
                apu_config[NV_PAPU_FECTL/4]=(control & ~NV_PAPU_FECTL_FETRAPREASON) |
                    NV_PAPU_FECTL_FEMETHMODE_TRAPPED | NV_PAPU_FECTL_FETRAPREASON_REQUESTED;
                apu_config[NV_PAPU_ISTS/4]|=NV_PAPU_ISTS_FETINTSTS;
                return;
            }
            id=next;
        }
    }
}

/* DirectSound publishes its effects-image command at byte 0x810 in GP
 * scratch. GPSADDR points to the scatter/gather table, not scratch itself.
 * Acknowledge the effects download in silent mode, as in the desktop boot. */
void ngb_audio_poll(void)
{
    advance_buffer_voices();
    report_idle_voice();
    uint32_t table = apu_config[NV_PAPU_GPSADDR / 4];
    if (!table || !(dsp_words[0][NV_PAPU_GPRST / 4] & NV_PAPU_GPRST_GPDSPRST))
        return;
    uint32_t page;
    memcpy(&page, ngb_dma_pointer(table, 4), 4);
    if (!page || (page & 4095))
        return;
    uint32_t *command = ngb_dma_pointer(page + 0x810, 4);
    if (*command == 2) { /* Update effect parameters in silent mode. */
        *command = 0;
    } else if (*command == 3) {
        *command = 0;
        ngb_kernel_log("APU GP acknowledged effects image (silent)");
    }
}

void *ngb_dsp_memory(uint32_t address, size_t bytes)
{
    unsigned bank = address >> 16;
    unsigned offset = address & 0xffff;
    if ((bank != 0xfe83 && bank != 0xfe85) || offset >= 0xc000 || bytes > 0xc000u - offset)
        return NULL;
    return (unsigned char *)dsp_words[bank == 0xfe85] + offset;
}
