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
    for (unsigned i=0;i<3;++i)
        for (int y=-3;y<=3;++y) for (int x=-3;x<=3;++x)
            if (x*x+y*y<=9) dst[(555+y)*(stride/4)+626+i*14+x] =
                i==tick%3 ? 0xff4141ae : 0xff444047;
    framebufferEnd(surface);
}
