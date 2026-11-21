#ifndef NGB_DIAG
#define NGB_DIAG 1
#endif
#include "scanout.h"
#ifdef __aarch64__
#include "wide_blit.h"
#endif
#include "frame_exchange.h"
#include "runtime.h"
#include "scene.h"
#ifdef NGB_DIRECT3D
#include "direct/output.h"
#endif
#include "contiguous.h"
#include <stdatomic.h>
#include <string.h>
#include <stdlib.h>

/* The worker owns guest RAM. Publish a snapshot for the UI before it is freed. */
static uint32_t frames[3][NGB_SCAN_H][NGB_SCAN_W];
static NgbExchange snapshots = NGB_EXCHANGE_INIT;
static atomic_uint generation, display_count;
static atomic_int last_snapshot = -1;
static atomic_int ready, blank, visible;
static atomic_int gpu_picture;
static uint32_t display_pitch;
static unsigned peak_brightness, fade_steps;
static uint64_t fade_start;

void ngb_scanout_reset(void)
{
    last_snapshot=-1;
    display_pitch=0;
    peak_brightness=fade_steps=0;
    fade_start=0;
    atomic_store(&visible, 0);
    atomic_store(&ready, 0);
    atomic_store(&blank, 0);
    atomic_store(&gpu_picture, 0);
}
void ngb_scanout_blank(int enabled)
{
    if (atomic_exchange(&blank, enabled != 0) != (enabled != 0)) atomic_fetch_add(&generation, 1);
}
void ngb_scanout_displayed(void) { atomic_fetch_add(&display_count, 1); }
unsigned ngb_scanout_display_count(void) { return atomic_load(&display_count); }
unsigned ngb_scanout_generation(void) { return atomic_load(&generation); }
int ngb_scanout_ready(void) { return atomic_load(&ready); }

int ngb_scanout_visible(void) { return atomic_load(&visible) && !atomic_load(&blank); }

void ngb_scanout_mode(uint32_t mode, uint32_t fmt, uint32_t pitch, uint32_t phys)
{
    if ((mode != 0x0802020e && mode != 0x1802020e) || fmt != 0x12 || pitch < NGB_SCAN_W*4 || pitch%4 || (phys&3))
        ngb_stop("unsupported scanout format or mode",mode);
    display_pitch=pitch;
    ngb_scanout_refresh(phys);
}

static void publish_snapshot(void)
{
    /* Ignore the guest's initial cleared surfaces when handing off the loading UI. */
    int first_picture = 0;
    if (!atomic_load(&visible)) {
        for (unsigned y=0; !first_picture && y<NGB_SCAN_H; y+=4)
            for (unsigned x=0; x<NGB_SCAN_W; x+=4)
                if (frames[snapshots.writer][y][x] & 0x00f0f0f0u) { first_picture=1; break; }
    }
    last_snapshot = snapshots.writer;
    ngb_publish(&snapshots);
    atomic_store(&gpu_picture, 0);
    if (first_picture) atomic_store(&visible,1);
    atomic_fetch_add(&generation, 1);
}

#ifdef NGB_DIRECT3D
void ngb_scanout_direct(const void *bgra)
{
    memcpy(frames[snapshots.writer], bgra, sizeof(frames[0]));
    publish_snapshot();
    atomic_store(&ready, 1);
}
#endif

void ngb_scanout_publish_gpu(void)
{
    atomic_store(&gpu_picture, 1);
    atomic_store(&visible, 1);
    atomic_fetch_add(&generation, 1);
    atomic_store(&ready, 1);
}

int ngb_scanout_is_gpu(void) { return atomic_load(&gpu_picture); }
int ngb_scanout_is_blank(void) { return atomic_load(&blank); }

const uint32_t *ngb_scanout_last_pixels(void)
{
    return ngb_scanout_ready() ? frames[ngb_latest(&snapshots)][0] : NULL;
}

void ngb_scanout_refresh(uint32_t phys)
{
    uint32_t pitch=display_pitch;
    if (!pitch) return;
    uint64_t n = (uint64_t)pitch*(NGB_SCAN_H-1)+4*NGB_SCAN_W;
    if (phys+n > 0x08000000u) ngb_stop("invalid scanout address",phys);
#ifdef NGB_DIRECT3D
    if (ngb_scene_active) return;  // the Vulkan thread publishes its own swap
#ifdef NGB_TEXTURE_PRELOAD
    extern void ngb_texture_title_tick(void);
    ngb_texture_title_tick();
#endif
#endif
    if (ngb_scene_active) {
        enum NgbPresent result = ngb_scene_present(phys, pitch, frames[snapshots.writer]);
        if (result == NGB_PRESENT_READY) {
            publish_snapshot();
            atomic_store(&ready, 1);
        }
        if (result != NGB_PRESENT_FALLBACK) return;
        ngb_scene_read_targets(phys, (size_t)n);
    }
    const unsigned char *src = ngb_scene_active ? ngb_contiguous_pointer_raw(0x80000000u+phys,(size_t)n) :
                                                 ngb_contiguous_pointer(0x80000000u+phys,(size_t)n);
    if (!src) ngb_stop("unmapped scanout",phys);
    if (last_snapshot >= 0 && !ngb_scanout_is_gpu()) {
        unsigned y=0;
        while (y<NGB_SCAN_H && !memcmp(frames[last_snapshot][y],src+y*pitch,NGB_SCAN_W*4)) ++y;
        if (y==NGB_SCAN_H) return;
    }
    uint32_t (*pixels)[NGB_SCAN_W]=frames[snapshots.writer];
    unsigned lit=0, peak=0;
    for (unsigned y=0; y<NGB_SCAN_H; ++y) {
        memcpy(pixels[y],src+y*pitch,NGB_SCAN_W*4);
        if (NGB_DIAG && peak_brightness<255) for (unsigned x=0; x<NGB_SCAN_W; ++x) {
            uint32_t c=pixels[y][x]&0xffffffu;
            lit+=c!=0;
            if ((c&255)>peak) peak=c&255;
        }
    }
#ifndef __SWITCH__
    const char *capture=getenv("NGB_CAPTURE_PPM");
    if (capture && peak>peak_brightness) {
        FILE *file=fopen(capture,"wb");
        if (file) {
            fprintf(file,"P6\n%u %u\n255\n",NGB_SCAN_W,NGB_SCAN_H);
            for (unsigned y=0;y<NGB_SCAN_H;++y) {
                unsigned char row[NGB_SCAN_W*3];
                for (unsigned x=0;x<NGB_SCAN_W;++x) {
                    uint32_t c=pixels[y][x];
                    row[3*x]=c>>16; row[3*x+1]=c>>8; row[3*x+2]=c;
                }
                fwrite(row,1,sizeof(row),file);
            }
            fclose(file);
        }
    }
#endif
    publish_snapshot();
    if (!NGB_DIAG) { atomic_store(&ready,1); return; }
    unsigned last=peak_brightness;
    if (peak>last) {
        peak_brightness=peak;
        if (!last) fade_start=ngb_elapsed_ns();
        ++fade_steps;
        if (last<164 && peak>=164) {
            char timing[96];
            snprintf(timing,sizeof(timing),"Warning fade steps=%u elapsed_ms=%llu peak=%u",
                     fade_steps,(unsigned long long)((ngb_elapsed_ns()-fade_start)/1000000),peak);
            ngb_kernel_log(timing);
        }
    }
    if (ngb_scanout_ready() && !((peak>0 && !last) || (peak>=64 && last<64))) return;
    char line[112];
    snprintf(line,sizeof(line),"scanout captured physical=%08x size=%ux%u pitch=%u nonblack=%u peak=%u",
             phys,NGB_SCAN_W,NGB_SCAN_H,pitch,lit,peak);
    ngb_kernel_log(line);
    atomic_store(&ready,1);
#ifndef __SWITCH__
    if (peak>=64 && lit>=4000 && getenv("NGB_TEST_VISIBLE_FRAME"))
        ngb_stop("verified visible guest frame",64);
#endif
}

uint32_t *ngb_scanout_movie_buffer(void)
{
#ifdef NGB_DIRECT3D
    if (ngb_scene_active) ngb_direct_finish_put();
#endif
    return frames[snapshots.writer][0];
}

void ngb_scanout_publish_movie(void)
{
    if (ngb_scene_active) ngb_scene_discard_present();
    publish_snapshot();
}

void ngb_scanout_blit(uint32_t *dst, unsigned stride, unsigned w, unsigned h)
{
    if (!dst || !ngb_scanout_ready() || stride<w || w<8 || h<8) return;
#ifdef NGB_PLAYER_BUILD
    extern int ngb_settings_standard_aspect(void);
    if(w==1280 && h==720 && ngb_settings_standard_aspect()){
        for(unsigned y=0;y<h;y++)for(unsigned x=0;x<160;x++)
            dst[(size_t)y*stride+x]=dst[(size_t)y*stride+1120+x]=0xff000000;
        dst+=160;w=960;
    }
#endif
    /* The Xbox widescreen signal is anamorphic: all 720x480 source pixels
     * map onto the Switch's 1280x720 framebuffer. No overscan or crop. */
    const uint32_t (*pixels)[NGB_SCAN_W]=frames[ngb_latest(&snapshots)];
    int is_blank=atomic_load(&blank);
#ifdef __aarch64__
    if (!is_blank && w==1280 && h==720 && NGB_SCAN_W==720 && NGB_SCAN_H==480) {
        ngb_wide_blit(dst,stride,pixels[0]);
        return;
    }
#endif
    static unsigned columns[1280], mapped_width;
    if (w <= 1280 && w != mapped_width) {
        for (unsigned x=0;x<w;++x) columns[x]=x*NGB_SCAN_W/w;
        mapped_width=w;
    }
    unsigned previous=NGB_SCAN_H;
    for (unsigned y=0;y<h;++y) {
        uint32_t *row=dst+(size_t)y*stride;
        unsigned sy=y*NGB_SCAN_H/h;
        if (sy==previous || (is_blank && y)) memcpy(row,row-stride,w*sizeof(*row));
        else if (is_blank) for (unsigned x=0;x<w;++x) row[x]=0xff000000u;
        else for (unsigned x=0;x<w;++x) {
            uint32_t v=pixels[sy][w<=1280?columns[x]:x*NGB_SCAN_W/w];
            row[x]=0xff000000u|(v&0xff00u)|((v>>16)&255u)|((v&255u)<<16);
        }
        previous=sy;
    }
}
