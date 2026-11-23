/* Pixel order matches libnx PIXEL_FORMAT_RGBA_8888. */
enum { splash_w = 640, splash_h = 360 };
static u32 splash[splash_w * splash_h];

static bool load_splash(void)
{
    FILE *f = fopen("romfs:/loading.rgba", "rb");
    if (!f) {
#ifdef NGB_PLAYER_BUILD
        return false;
#else
        /* Standalone developer packages do not carry the player artwork. */
        for (size_t i=0;i<sizeof splash/sizeof *splash;++i) splash[i]=0xff141010;
        return true;
#endif
    }
    bool ok = fread(splash, 1, sizeof splash, f) == sizeof splash;
    fclose(f);
    return ok;
}

#if defined(NGB_PLAYER_BUILD) && defined(NGB_DIRECT3D)
#include "loading_labels.h"

static void loading_number(char out[14], uint32_t number)
{
    char digits[11];
    int n = snprintf(digits, sizeof digits, "%u", number);
    for (int i = 0; i < n; ++i) {
        if (i && (n-i) % 3 == 0) *out++ = ',';
        *out++ = digits[i];
    }
    *out = 0;
}

static void loading_status(u32 *dst, unsigned stride, NgbLoadingProgress progress)
{
    const bool reading = progress.total == NGB_LOADING_READ_CACHE;
    char counts[32] = "";
    if (!reading) {
        char ready[14], total[14];
        loading_number(ready, progress.ready);
        loading_number(total, progress.total);
        snprintf(counts, sizeof counts, "  %s / %s", ready, total);
    }
    int left = (NGB_SCREEN_W - loading_label_width - panel_text_width(counts)) / 2;
    /* Both lines use the untextured background below the original Loading artwork. */
    static const u32 ink[] = {0, 0xff5b5857, 0xffa29e9c, 0xffebe7e4};
    for (int y = 0; y < loading_label_height; ++y) {
        const unsigned char *row = loading_labels[!reading][y];
        for (int x = 0; x < loading_label_width; ++x) {
            unsigned alpha = row[x/4] >> (6-2*(x%4)) & 3;
            if (alpha) dst[(546+y)*stride+left+x] = ink[alpha];
        }
    }
    if (reading) return;
    panel_text(dst, stride, left+loading_label_width, 547, counts, ink[3]);
    const unsigned width = 384;
    unsigned filled = (uint64_t)width * progress.ready / progress.total;
    for (int y = 591; y < 597; ++y) {
        u32 *bar = dst+y*stride+(NGB_SCREEN_W-width)/2;
        for (unsigned x = 0; x < width; ++x)
            bar[x] = x < filled ? 0xff4747bb : 0xff393438;
    }
}
#endif

static void show_loading(Framebuffer *surface, unsigned tick)
{
    u32 stride;
    u32 *dst = framebufferBegin(surface, &stride);
    for (unsigned y = 0; y < splash_h; ++y) {
        u32 *row = dst + 2*y*(stride/4);
        for (unsigned x = 0; x < splash_w; ++x)
            row[x*2] = row[x*2+1] = splash[y*splash_w+x];
        memcpy(row+stride/4,row,1280*sizeof(u32));
    }
#if defined(NGB_PLAYER_BUILD) && defined(NGB_DIRECT3D)
    NgbLoadingProgress progress = ngb_loading_progress();
    if (progress.total) {
        loading_status(dst, stride/4, progress);
        framebufferEnd(surface);
        return;
    }
#endif
    for (unsigned i=0;i<3;++i)
        for (int y=-3;y<=3;++y) for (int x=-3;x<=3;++x)
            if (x*x+y*y<=9) dst[(555+y)*(stride/4)+626+i*14+x] =
                i==tick%3 ? 0xff4141ae : 0xff444047;
    framebufferEnd(surface);
}
