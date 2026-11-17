/* Screen-space, single-stage textured strips issued by the startup compositor. */
#include <math.h>
#include <stdbool.h>
#include "d3d/d3d8_swizzle.h"

#include "menu_gpu.h"
_Static_assert(sizeof(struct screen_vertex) == 28, "inline vertex layout");

enum surface_access { CPU_TARGET, TEXTURE_SOURCE, OVERLAY_TARGET };

static uint32_t *draw_surface(uint32_t context, uint32_t offset, size_t bytes, enum surface_access access)
{
    uint32_t instance = state.dma3d[(context - 0x180) / 4];
    uint32_t desc[3];
    void *object = ngb_instance_aperture(NGB_PRAMIN_BASE + instance, sizeof(desc));
    if (!object)
        ngb_stop("missing draw DMA object", instance);
    memcpy(desc, object, sizeof(desc));
    uint32_t cls = desc[0] & NV_DMA_CLASS;
    uint64_t base = ((desc[2] & NV_DMA_ADDRESS) | (desc[0] >> 20)) + (uint64_t)offset;
    if ((base & 3) || (desc[0] & NV_DMA_TARGET) ||
        (cls != NV_DMA_IN_MEMORY_CLASS &&
         cls != (access == TEXTURE_SOURCE ? NV_DMA_FROM_MEMORY_CLASS : NV_DMA_TO_MEMORY_CLASS)) ||
        (uint64_t)offset + bytes > (uint64_t)desc[1] + 1 || base + bytes > XBOX_CONTIG_SIZE)
        ngb_stop("invalid draw DMA range", offset);
    uint32_t *ptr = access == OVERLAY_TARGET ? ngb_contiguous_pointer_raw(XBOX_CONTIG_BASE + base, bytes) :
                                  ngb_contiguous_pointer(XBOX_CONTIG_BASE + base, bytes);
    if (!ptr)
        ngb_stop("unmapped draw surface", offset);
    return ptr;
}

static uint32_t mix_texels(uint32_t a, uint32_t b, float t)
{
    if (a == b || t == 0.0f) return a;
    uint32_t out = 0;
    for (unsigned shift = 0; shift < 32; shift += 8) {
        float x = (a >> shift) & 255, y = (b >> shift) & 255;
        out |= (uint32_t)(x + (y - x) * t + 0.5f) << shift;
    }
    return out;
}

static uint32_t blend_sprite(uint32_t dst, uint32_t src, int additive)
{
    unsigned alpha = src >> 24;
    if (!alpha) return dst;
    /* Two 8-bit channels fit in separate halfwords during weighted
     * addition. Divide each lane by 255 with round-to-nearest. */
    const uint32_t mask=0x00ff00ff, bias=0x00800080;
    unsigned inv=additive ? 0 : 255-alpha;
    uint32_t rb=(src&mask)*alpha+(dst&mask)*inv+bias;
    uint32_t ga=((src>>8)&mask)*alpha+((dst>>8)&mask)*inv+bias;
    rb=((rb+((rb>>8)&mask))>>8)&mask;
    ga=((ga+((ga>>8)&mask))>>8)&mask;
    if (additive) {
        rb+=(dst&mask); ga+=((dst>>8)&mask);
        uint32_t cr=(rb>>8)&0x00010001, cg=(ga>>8)&0x00010001;
        rb=(rb | (cr*255))&mask;
        ga=(ga | (cg*255))&mask;
    }
    return rb|(ga<<8);
}

/* The menu rotates and pans several alpha-only overlays. Their RGB comes
 * entirely from the diffuse colour. Walk the affine UVs once per pixel
 * and filter only the alpha channel; the two original strip triangles
 * agree on this mapping for a parallelogram. */
static int draw_alpha_overlay(const struct screen_vertex v[4], const uint8_t *tex,
                              unsigned tw, unsigned th, uint32_t *dst, unsigned stride,
                              unsigned width, unsigned height, int additive)
{
    for (unsigned i=0; i<4; ++i)
        if (v[i].color!=v[0].color || v[i].u!=v[i&1].u || v[i].v!=v[i&2].v) return 0;
    float bx=v[1].x-v[0].x, by=v[1].y-v[0].y, cx=v[2].x-v[0].x, cy=v[2].y-v[0].y;
    if (fabsf(v[3].x-v[2].x-bx)>0.00025f || fabsf(v[3].y-v[2].y-by)>0.00025f) return 0;
    float det=bx*cy-by*cx;
    if (fabsf(det)<0.001f) return 0;
    unsigned opacity=v[0].color>>24;
    if (!opacity) return 1;
    unsigned mx,my;
    xbox_swizzle_masks(tw,th,&mx,&my);
    uint32_t cols[4097], rows[4097];
    cols[0]=rows[0]=0;
    for (unsigned x=1; x<tw; ++x) cols[x]=(cols[x-1]-mx)&mx;
    for (unsigned y=1; y<th; ++y) rows[y]=(rows[y-1]-my)&my;
    cols[tw]=cols[tw-1]; rows[th]=rows[th-1];
    uint32_t colors[256];
    for (unsigned i=0;i<256;++i)
        colors[i]=(v[0].color&0xffffffu) | (((i*opacity+127)/255)<<24);
    int left=width, top=height, right=0, bottom=0;
    for (unsigned i=0;i<4;++i) {
        int x=(int)ceilf(v[i].x), y=(int)ceilf(v[i].y);
        if (x<left) left=x;
        if (x>right) right=x;
        if (y<top) top=y;
        if (y>bottom) bottom=y;
    }
    if (left<0) left=0;
    if (top<0) top=0;
    if (right>(int)width) right=width;
    if (bottom>(int)height) bottom=height;
    float du=(v[1].u-v[0].u)*tw, dv=(v[2].v-v[0].v)*th;
    float ds=cy/det, dt=-by/det;
    for (int y=top;y<bottom;++y) {
        float s0=((left-v[0].x)*cy-(y-v[0].y)*cx)/det;
        float t0=(bx*(y-v[0].y)-by*(left-v[0].x))/det;
        uint32_t *row=dst+y*stride;
        for (int x=left;x<right;++x) {
            float s=s0+(x-left)*ds, t=t0+(x-left)*dt;
            if (s<0 || s>1 || t<0 || t>1) continue;
            float u=fminf(tw-1,fmaxf(0,v[0].u*tw+s*du-0.5f));
            float w=fminf(th-1,fmaxf(0,v[0].v*th+t*dv-0.5f));
            unsigned ix=(unsigned)u, iy=(unsigned)w;
            unsigned l=cols[ix], r=cols[ix+1], a=rows[iy], b=rows[iy+1];
            unsigned p=tex[a|l], q=tex[a|r], k=tex[b|l], n=tex[b|r];
            if (!(p|q|k|n)) continue;
            float fx=u-ix, fy=w-iy;
            int ab=(int)(p+((int)q-(int)p)*fx+0.5f);
            int cd=(int)(k+((int)n-(int)k)*fx+0.5f);
            unsigned alpha=(unsigned)(ab+(cd-ab)*fy+0.5f);
            uint32_t color=colors[alpha];
            row[x]=blend_sprite(row[x],color,additive);
        }
    }
    return 1;
}

/* Reuse the completed rectangle only when the texture, palette, vertices
 * and the underlying destination pixels are all identical. The CPU can
 * modify guest RAM without going through the graphics command processor. */
enum { MEMO_PIXELS = 720*480, MEMO_TEXELS = 512*512 };
struct sprite_memo {
    struct screen_vertex vertices[4];
    uint32_t format, palette[256], before[MEMO_PIXELS], after[MEMO_PIXELS];
    unsigned palette_size, width, height, additive, valid;
    uint8_t texture[MEMO_TEXELS];
};
static struct sprite_memo sprite_memos[2];
struct sprite_rect { unsigned x,y,w,h; };

static struct sprite_memo *sprite_memo_begin(const struct screen_vertex v[4],
        const uint8_t *texture, unsigned texels, uint32_t format, const uint32_t *palette,
        unsigned palette_size, unsigned additive, uint32_t *dst, unsigned stride,
        unsigned width, unsigned height, struct sprite_rect *rect, int *hit)
{
    if (texels>MEMO_TEXELS || ((format>>8)&255)!=0x0b) return NULL;
    float xmin=v[0].x, xmax=xmin, ymin=v[0].y, ymax=ymin;
    for (unsigned i=1; i<4; ++i) {
        xmin=fminf(xmin,v[i].x); xmax=fmaxf(xmax,v[i].x);
        ymin=fminf(ymin,v[i].y); ymax=fmaxf(ymax,v[i].y);
    }
    int x=fmaxf(0,ceilf(xmin)), right=fminf(width,ceilf(xmax));
    int y=fmaxf(0,ceilf(ymin)), bottom=fminf(height,ceilf(ymax));
    if (right<=x || bottom<=y) return NULL;
    unsigned area=(right-x)*(bottom-y);
    if (area<48*1024 || area>MEMO_PIXELS) return NULL;
    /* Two halves of a split backdrop can use the same texture and palette. */
    static unsigned replace;
    *rect=(struct sprite_rect){x,y,right-x,bottom-y};
    struct sprite_memo *slot=NULL;
    for (unsigned i=0;i<2;++i) {
        struct sprite_memo *entry=&sprite_memos[i];
        if (!entry->valid || entry->format!=format || entry->width!=width || entry->height!=height ||
            entry->additive!=additive || entry->palette_size!=palette_size ||
            memcmp(entry->vertices,v,sizeof(entry->vertices))) continue;
        slot=entry;
        if (memcmp(entry->palette,palette,palette_size*4) || memcmp(entry->texture,texture,texels)) break;
        unsigned row=0;
        while (row<rect->h && !memcmp(dst+(y+row)*stride+x,entry->before+row*rect->w,rect->w*4)) ++row;
        if (row!=rect->h) break;
        for (row=0; row<rect->h; ++row)
            memcpy(dst+(y+row)*stride+x,entry->after+row*rect->w,rect->w*4);
        *hit=1;
        return entry;
    }
    if (!slot) slot=&sprite_memos[replace++%2];
    slot->valid=0;
    slot->format=format; slot->width=width; slot->height=height;
    slot->palette_size=palette_size; slot->additive=additive;
    memcpy(slot->vertices,v,sizeof(slot->vertices));
    memcpy(slot->texture,texture,texels);
    memcpy(slot->palette,palette,palette_size*4);
    for (unsigned row=0; row<rect->h; ++row)
        memcpy(slot->before+row*rect->w,dst+(y+row)*stride+x,rect->w*4);
    return slot;
}

static void sprite_memo_end(struct sprite_memo *entry,struct sprite_rect rect,const uint32_t *dst,unsigned stride)
{
    if (!entry) return;
    for (unsigned row=0; row<rect.h; ++row)
        memcpy(entry->after+row*rect.w,dst+(rect.y+row)*stride+rect.x,rect.w*4);
    entry->valid=1;
}

#include "menu_thumbnails.inc"

static void raster_sprite(const struct screen_vertex v[4], unsigned width, unsigned height,
                          uint32_t tf, const uint8_t *tex, unsigned tw, unsigned th,
                          uint32_t *dst, unsigned pitch, uint32_t lut[256], unsigned count,
                          int standard, int alpha_only, int additive, int allow_memo)
{
    struct sprite_rect rect={0};
    int hit=0;
    struct sprite_memo *memo=allow_memo ? sprite_memo_begin(v,tex,tw*th,tf,lut,count,additive,
                                               dst,pitch/4,width,height,&rect,&hit) : NULL;
    if (hit) return;
    uint32_t mx, my;
    xbox_swizzle_masks(tw, th, &mx, &my);
    if (!standard) {
        for (unsigned triangle = 0; triangle < 2; ++triangle) {
            const struct screen_vertex *a = &v[triangle], *b = &v[triangle+1], *c = &v[triangle+2];
            float bx=b->x-a->x, by=b->y-a->y, cx=c->x-a->x, cy=c->y-a->y;
            float det=bx*cy-by*cx;
            if (!det) continue;
            int left=fmaxf(0,ceilf(fminf(a->x,fminf(b->x,c->x))));
            int top=fmaxf(0,ceilf(fminf(a->y,fminf(b->y,c->y))));
            int right=fminf(width,ceilf(fmaxf(a->x,fmaxf(b->x,c->x))));
            int bottom=fminf(height,ceilf(fmaxf(a->y,fmaxf(b->y,c->y))));
            for (int y=top; y<bottom; ++y) for (int x=left; x<right; ++x) {
                float wb=((x-a->x)*cy-(y-a->y)*cx)/det;
                float wc=(bx*(y-a->y)-by*(x-a->x))/det;
                float wa=1-wb-wc;
                /* The second triangle shares its a-b edge with the first. */
                if (wa<0 || wb<0 || wc<0 || (triangle && wc==0)) continue;
                float sx=fminf(tw-1,fmaxf(0,(wa*a->u+wb*b->u+wc*c->u)*tw-0.5f));
                float sy=fminf(th-1,fmaxf(0,(wa*a->v+wb*b->v+wc*c->v)*th-0.5f));
                unsigned tx=sx, ty=sy;
                unsigned l=swizzle_deposit(tx,mx), r=swizzle_deposit(tx+1<tw?tx+1:tx,mx);
                unsigned t=swizzle_deposit(ty,my), d=swizzle_deposit(ty+1<th?ty+1:ty,my);
                unsigned ia=tex[t|l], ib=tex[t|r], ic=tex[d|l], id=tex[d|r];
                if ((ia|ib|ic|id)>=count) ngb_stop("sprite palette index outside range",count);
                uint32_t sample=mix_texels(mix_texels(lut[ia],lut[ib],sx-tx),
                                           mix_texels(lut[ic],lut[id],sx-tx),sy-ty);
                uint32_t color=0;
                for (unsigned shift=0;shift<32;shift+=8) {
                    float tint=wa*((a->color>>shift)&255)+wb*((b->color>>shift)&255)+wc*((c->color>>shift)&255);
                    color |= (uint32_t)(tint*((sample>>shift)&255)/255.0f+0.5f)<<shift;
                }
                uint32_t *pixel=&dst[y*(pitch/4)+x];
                *pixel=blend_sprite(*pixel,color,additive);
            }
        }
        sprite_memo_end(memo,rect,dst,pitch/4);
        return;
    }
    for (unsigned i = 0; i < count; i++) {
        uint32_t col = 0;
        for (unsigned shift = 0; shift < 32; shift += 8)
            col |= ((((lut[i] >> shift) & 255) * ((v[0].color >> shift) & 255) + 127) / 255) << shift;
        lut[i] = col;
    }
    int x0 = fmaxf(0, ceilf(v[0].x)), x1 = fminf(width, ceilf(v[1].x));
    int y0 = fmaxf(0, ceilf(v[0].y)), y1 = fminf(height, ceilf(v[2].y));
    if(x1<=x0 || y1<=y0)return;
    Thumb *thumb=NULL;
    unsigned sw=x1-x0,sh=y1-y0;
    int strip=allow_memo && !alpha_only && !additive && tw==256 && th==64 &&
        sw>=600 && sw<=STRIP_W && sh<=STRIP_H &&
        ((uintptr_t)dst+(size_t)pitch*height<=(uintptr_t)tex || (uintptr_t)tex+tw*th<=(uintptr_t)dst);
    if(strip && title_strip_hit(v,x0,y0,sw,sh,tex,lut,count)){
        for(unsigned y=0;y<sh;y++){
            uint32_t *row=dst+(y+y0)*(pitch/4)+x0;
            const uint32_t *src=title_strip.pixels+y*sw;
            if(title_strip.opaque)memcpy(row,src,sw*4);
            else for(unsigned x=0;x<sw;x++)row[x]=blend_sprite(row[x],src[x],0);
        }
        return;
    }
    if(tw==1024 && th==1024 && !alpha_only && !additive && allow_memo &&
       ((uintptr_t)dst+(size_t)pitch*height<=(uintptr_t)tex ||
        (uintptr_t)tex+tw*th<=(uintptr_t)dst)){
        int cached=0;
        thumb=thumbnail(v,tex,lut,count,x0,y0,x1-x0,y1-y0,&cached);
        if(thumb) MP_ADD(cached?MP_THUMB_HIT:MP_THUMB_MISS,0,0);
        if(cached){
            for(int y=y0;y<y1;y++){
                uint32_t *row=dst+y*(pitch/4)+x0;
                const uint32_t *src=thumb->pixels+(y-y0)*thumb->w;
                if(thumb->opaque)memcpy(row,src,thumb->w*4);
                else for(unsigned x=0;x<thumb->w;x++)row[x]=blend_sprite(row[x],src[x],0);
            }
            return;
        }
    }
    struct { unsigned left, right; float fraction; } columns[2048];
    for (int x = x0; x < x1; x++) {
        float ax = (x - v[0].x) / (v[1].x - v[0].x);
        float sx = fminf(tw - 1, fmaxf(0, (v[0].u + ax * (v[1].u - v[0].u)) * tw - 0.5f));
        unsigned tx = sx, nx = tx + 1 < tw ? tx + 1 : tx;
        unsigned col = swizzle_deposit(tx, mx), right = swizzle_deposit(nx, mx);
        columns[x].left = col;
        columns[x].right = right;
        columns[x].fraction = sx - tx;
    }
    for (int y = y0; y < y1; y++) {
        float ay = (y - v[0].y) / (v[2].y - v[0].y);
        float sy = fminf(th - 1, fmaxf(0, (v[0].v + ay * (v[2].v - v[0].v)) * th - 0.5f));
        unsigned ty = sy, ny = ty + 1 < th ? ty + 1 : ty;
        unsigned row = swizzle_deposit(ty, my), next = swizzle_deposit(ny, my);
        if (alpha_only) {
            float fy=sy-ty;
            uint32_t rgb=v[0].color&0xffffffu;
            uint32_t *pixels=dst+y*(pitch/4);
            for (int x=x0; x<x1; ++x) {
                unsigned l=columns[x].left, r=columns[x].right;
                unsigned a=tex[row|l], b=tex[row|r], c=tex[next|l], d=tex[next|r];
                if (!(a|b|c|d)) continue;
                int aa=lut[a]>>24, ab=lut[b]>>24, ac=lut[c]>>24, ad=lut[d]>>24;
                float fx=columns[x].fraction;
                int top=(int)(aa+(ab-aa)*fx+0.5f);
                int bottom=(int)(ac+(ad-ac)*fx+0.5f);
                unsigned opacity=(unsigned)(top+(bottom-top)*fy+0.5f);
                if (opacity) pixels[x]=blend_sprite(pixels[x],rgb|(opacity<<24),additive);
            }
            continue;
        }
        for (int x = x0; x < x1; x++) {
            unsigned col = columns[x].left, right = columns[x].right;
            uint8_t ia = tex[row | col], ib = tex[row | right], ic = tex[next | col], id = tex[next | right];
            if ((ia | ib | ic | id) >= count)
                ngb_stop("sprite palette index outside range", count);
            uint32_t a = mix_texels(lut[ia], lut[ib], columns[x].fraction);
            uint32_t b = mix_texels(lut[ic], lut[id], columns[x].fraction);
            uint32_t color = mix_texels(a, b, sy - ty), alpha = color >> 24;
            if(strip){title_strip.pixels[(y-y0)*sw+x-x0]=color;title_strip.opaque&=alpha==255;}
            if(thumb){thumb->pixels[(y-y0)*thumb->w+x-x0]=color;thumb->opaque&=alpha==255;}
            if (alpha) {
                uint32_t *pixel = &dst[y * (pitch / 4) + x];
                *pixel = blend_sprite(*pixel, color, additive);
            }
        }
    }
    if(strip)title_strip.valid=1;
    if(thumb)thumb->valid=1;
    sprite_memo_end(memo,rect,dst,pitch/4);
}

/* The two menu backdrop strips and the title portrait vary only their
 * opacity during the fade. Filter the opaque source once at full strength.
 * A zero alpha in the saved image marks pixels outside the strip. */
enum { BACKDROP_TEXELS = 1024*512 };
struct backdrop {
    struct screen_vertex vertices[4];
    uint32_t image[MEMO_PIXELS], palette[256];
    struct { uint16_t left, right; int solid; } span[480];
    uint8_t texture[BACKDROP_TEXELS];
    unsigned format, count;
};
static struct backdrop backdrops[2];
static unsigned next_backdrop;

static int draw_backdrop(const struct screen_vertex v[4], unsigned width, unsigned height,
                         uint32_t tf, const uint8_t *tex, unsigned tw, unsigned th,
                         uint32_t *dst, unsigned pitch, const uint32_t *palette, unsigned count,
                         int standard, int additive)
{
    if (width != 720 || height != 480 || tw*th < 512*512 || tw*th > BACKDROP_TEXELS ||
        (v[0].color & 0xffffff) != 0xffffff || additive) return 0;
    struct screen_vertex opaque[4];
    memcpy(opaque,v,sizeof(opaque));
    for (unsigned i=0; i<4; ++i) {
        if (v[i].color != v[0].color) return 0;
        opaque[i].color=UINT32_MAX;
    }
    unsigned alpha=v[0].color>>24;
    if (!alpha) return 1;
    size_t bytes=tw*th;
    uintptr_t target=(uintptr_t)dst, source=(uintptr_t)tex;
    if (source < target+(height-1)*pitch+width*4 && target < source+bytes) return 0;
    struct backdrop *slot=NULL;
    for (unsigned i=0; i<2; ++i) {
        struct backdrop *candidate=&backdrops[i];
        if (candidate->format==tf && candidate->count==count &&
            !memcmp(candidate->vertices,opaque,sizeof(opaque)) &&
            !memcmp(candidate->palette,palette,count*4) && !memcmp(candidate->texture,tex,bytes)) {
            slot=candidate;
            break;
        }
    }
    if (!slot) {
        for (unsigned i=0; i<bytes; ++i)
            if (tex[i]>=count || palette[tex[i]]>>24 != 255) return 0;
        slot=&backdrops[next_backdrop++ % 2];
        memcpy(slot->texture,tex,bytes);
        memcpy(slot->palette,palette,count*4);
        memcpy(slot->vertices,opaque,sizeof(opaque));
        slot->format=tf;
        slot->count=count;
        memset(slot->image,0,width*height*4);
        uint32_t lut[256];
        memcpy(lut,palette,count*4);
        raster_sprite(opaque,width,height,tf,tex,tw,th,slot->image,width*4,lut,count,
                      standard,0,0,0);
        for (unsigned y=0; y<height; ++y) {
            unsigned left=width, right=0, covered=0;
            for (unsigned x=0; x<width; ++x) {
                if (!(slot->image[y*width+x]>>24)) continue;
                if (left==width) left=x;
                right=x+1;
                ++covered;
            }
            slot->span[y].left=covered ? left : 0;
            slot->span[y].right=right;
            slot->span[y].solid=(covered && covered==right-left);
        }
    }
    for (unsigned y=0; y<height; ++y) {
        uint32_t *row=dst+y*(pitch/4);
        const uint32_t *colors=slot->image+y*width;
        unsigned left=slot->span[y].left, right=slot->span[y].right;
        if (slot->span[y].solid) {
            if (alpha==255) memcpy(row+left,colors+left,(right-left)*4);
            else for (unsigned x=left; x<right; ++x)
                row[x]=blend_sprite(row[x],(colors[x]&0xffffff)|(alpha<<24),0);
        } else for (unsigned x=left; x<right; ++x) {
            if (colors[x]>>24)
                row[x]=blend_sprite(row[x],(colors[x]&0xffffff)|(alpha<<24),0);
        }
    }
    return 1;
}

static void draw_alpha_sprite(const struct screen_vertex v[4], unsigned width, unsigned height, uint32_t fmt,
                              uint32_t tf)
{
    uint32_t *m = state.methods;
    int additive = m[0x348 / 4] == 1;
    unsigned tw = 1u << ((tf >> 20) & 15), th = 1u << ((tf >> 24) & 15);
    unsigned pitch = m[0x20c / 4] & 65535;
    if ((fmt & 0xfff) != 0x128 || !width || !height || width > 2048 || height > 2048 || tw > 4096 ||
        th > 4096 || pitch % 4 || pitch < 4 * width || (tf & 3) != 2 || m[0xac0 / 4] != 0x08040000 ||
        m[0x260 / 4] != 0x18140000 || m[0x288 / 4] != 12 || m[0x28c / 4] != 0x1c80 || m[0x344 / 4] != 0x302 ||
        (!additive && m[0x348 / 4] != 0x303) || m[0x350 / 4] != 0x8006 || m[0x30c / 4] || m[0x300 / 4])
        ngb_stop("unsupported sprite state", tf);
    for (unsigned i = 0; i < 4; i++)
        if (!isfinite(v[i].x) || fabsf(v[i].x) > 32768 || !isfinite(v[i].y) || fabsf(v[i].y) > 32768 ||
            !isfinite(v[i].u) || !isfinite(v[i].v) || v[i].z != 0 || v[i].w != 1)
            ngb_stop("unsupported sprite geometry", i);
    int standard = v[1].x > v[0].x && v[2].y > v[0].y;
    for (unsigned i = 0; i < 4; ++i)
        standard &= v[i].x == v[i&1].x && v[i].y == v[i&2].y && v[i].u == v[i&1].u &&
                    v[i].v == v[i&2].v && v[i].color == v[0].color;
    if(!((v[0].color|v[1].color|v[2].color|v[3].color)>>24))return;
    uint8_t *tex = (uint8_t *)draw_surface(NV097_SET_CONTEXT_DMA_B, m[0x1b00 / 4], tw * th, TEXTURE_SOURCE);
    uint32_t *dst =
        draw_surface(NV097_SET_CONTEXT_DMA_COLOR, m[0x210 / 4], (height - 1) * pitch + 4 * width, OVERLAY_TARGET);
    int alpha_only = ((tf >> 8) & 255) == 0x19;
    if (alpha_only && ngb_menu_gpu_overlay(v,tex,tw,th,dst,pitch/4,width,height,additive)) return;
    ngb_menu_gpu_sync(dst,(height-1)*pitch+4*width);
    if (!standard && alpha_only &&
        draw_alpha_overlay(v,tex,tw,th,dst,pitch/4,width,height,additive)) return;
    uint32_t lut[256];
    unsigned count = 256;
    if (((tf >> 8) & 255) == 0x0b) {
        uint32_t p = m[0x1b20 / 4];
        count >>= (p >> 2) & 3;
        uint32_t *palette = draw_surface((p & 1) ? NV097_SET_CONTEXT_DMA_B : NV097_SET_CONTEXT_DMA_A,
                                         p & 0xffffffc0u, count * 4, TEXTURE_SOURCE);
        if (draw_backdrop(v,width,height,tf,tex,tw,th,dst,pitch,palette,count,standard,additive)) return;
        memcpy(lut, palette, count * 4);
    } else {
        for (unsigned i = 0; i < 256; i++)
            lut[i] = (i << 24) | 0xffffff;
    }
    raster_sprite(v,width,height,tf,tex,tw,th,dst,pitch,lut,count,standard,alpha_only,additive,1);
}

/* Sofdec uploads its decoded ARGB frame as a linear texture. With a white
 * primary colour, no blending and texel centres aligned to pixels, the
 * combiner copies RGB one-to-one and writes the primary alpha. */
static void draw_movie_strip(void)
{
    const uint32_t *m=state.methods;
    unsigned width=m[0x200/4]>>16, height=m[0x204/4]>>16;
    unsigned src_pitch=m[0x1b10/4]>>16, dst_pitch=m[0x20c/4]&65535;
    if (!width || !height || width>2048 || height>2048 || m[0x208/4]!=0x128 ||
        m[0x1b04/4]!=0x11229 || m[0x1b1c/4]!=(width<<16 | height) ||
        (src_pitch|dst_pitch)%4 || src_pitch<4*width || dst_pitch<4*width ||
        m[0x300/4] || m[0x304/4] || m[0x30c/4] || m[0x358/4]!=0x01010101 ||
        m[0x194c/4]!=UINT32_MAX || m[0x1e60/4]!=1 || m[0x1e70/4]!=1 ||
        m[0xac0/4]!=0x08040000 || m[0x260/4]!=0x2014 || m[0x1e40/4]!=0xc00 ||
        m[0xaa0/4]!=0xc00 || m[0x288/4]!=12 || m[0x28c/4]!=0x1c80)
        ngb_stop("unsupported linear movie strip state",m[0x1b04/4]);
    for (unsigned i=0;i<16;i++) {
        unsigned format=i==0 ? 0x42 : i==9 ? 0x22 : 2;
        if ((m[0x1760/4+i]&255)!=format) ngb_stop("unsupported movie vertex format",i);
    }
    float vertices[4][6];
    memcpy(vertices,state.inline_words,sizeof(vertices));
    /* Retail also presents movies in an inset or cropped screen rectangle.
     * NV2A screen coordinates already include the half-pixel offset; covered
     * pixels have integer centres. Keep the full-screen copy as a fast path. */
    const float *a=vertices[0], *b=vertices[1], *c=vertices[2];
    for (unsigned i=0;i<4;i++) {
        const float *p=vertices[i];
        for (unsigned j=0;j<6;j++)
            if (!isfinite(p[j]) || fabsf(p[j])>65536)
                ngb_stop("invalid movie vertex",i);
        if (p[0]!=vertices[i&1][0] || p[1]!=vertices[i&2][1] ||
            p[4]!=vertices[i&1][4] || p[5]!=vertices[i&2][5] ||
            p[3]!=a[3] || !p[3])
            ngb_stop("nonrectangular movie strip",i);
    }
    if (b[0]==a[0] || c[1]==a[1]) return;
    int left=fmaxf(0,ceilf(fminf(a[0],b[0]))), right=fminf(width,ceilf(fmaxf(a[0],b[0])));
    int top=fmaxf(0,ceilf(fminf(a[1],c[1]))), bottom=fminf(height,ceilf(fmaxf(a[1],c[1])));
    if (right<=left || bottom<=top) return;
    const uint32_t *src=ngb_prologue_pixels();
    if(src && width==720 && height==480) {
        src_pitch=720*4;
        for(unsigned j=0;j<4;j++){
            vertices[j][4]=(j&1)?720:0; vertices[j][5]=(j&2)?480:0;
        }
    } else src=draw_surface(NV097_SET_CONTEXT_DMA_A,m[0x1b00/4],(height-1)*src_pitch+width*4,TEXTURE_SOURCE);
    uint32_t *dst=draw_surface(NV097_SET_CONTEXT_DMA_COLOR,m[0x210/4],(height-1)*dst_pitch+width*4,CPU_TARGET);
    if (a[4]==0 && b[4]==0 && a[5]==0 && c[5]==0) {
        unsigned address=m[NV097_SET_TEXTURE_ADDRESS/4], mag=(m[NV097_SET_TEXTURE_FILTER/4]>>24)&15;
        if (mag!=1 && (address&0x707)!=0x303) ngb_stop("unsupported movie origin sampler",address);
        uint32_t color=0xff000000u|src[0];
        for(int y=top;y<bottom;y++)for(int x=left;x<right;x++)dst[y*(dst_pitch/4)+x]=color;
        return;
    }
    if(a[0]==-0.5f && b[0]==width-0.5f && a[1]==-0.5f && c[1]==height-0.5f &&
       a[4]==0 && b[4]==width && a[5]==0 && c[5]==height) {
        for(unsigned y=0;y<height;y++)for(unsigned x=0;x<width;x++)
            dst[y*(dst_pitch/4)+x]=0xff000000u|src[y*(src_pitch/4)+x];
    } else if (width==720 && height==480 && a[0]==-0.5f && b[0]==719.5f &&
               a[1]==-80.5f && c[1]==559.5f && a[4]==0 && b[4]==720 &&
               a[5]==0 && c[5]==480 && ((m[NV097_SET_TEXTURE_FILTER/4]>>24)&15)==2) {
        /* Original widescreen prologue: horizontal texels already align,
         * and the vertical centres have exact eighth-texel coordinates.
         * Blend contiguous rows without four sampler lookups per pixel. */
        for (unsigned y=0;y<480;y++) {
            unsigned v=479+6*y, w=v&7;
            const uint32_t *lo=src+(v>>3)*(src_pitch/4), *hi=lo+src_pitch/4;
            uint32_t *out=dst+y*(dst_pitch/4);
            for (unsigned x=0;x<720;x++) {
                const uint32_t mask=0xff00ffu;
                uint32_t a0=lo[x],a1=hi[x];
                uint32_t rb=(((a0&mask)*(8-w)+(a1&mask)*w+0x40004u)>>3)&mask;
                uint32_t g=(((a0&0xff00u)*(8-w)+(a1&0xff00u)*w+0x400u)>>3)&0xff00u;
                out[x]=0xff000000u|rb|g;
            }
        }
    } else {
        float du=(b[4]-a[4])/(b[0]-a[0]), dv=(c[5]-a[5])/(c[1]-a[1]);
        unsigned filter=m[NV097_SET_TEXTURE_FILTER/4];
        unsigned linear=fmaxf(fabsf(du),fabsf(dv))>1 ? ((filter>>16)&15)!=1 : ((filter>>24)&15)!=1;
        static int ix[2048],nx[2048];static float fx[2048]; /* guest worker only */
        for(int x=left;x<right;x++){
            float u=fminf(width-1,fmaxf(0,a[4]+(x-a[0])*du-(linear?0.5f:0)));
            ix[x]=(int)u;nx[x]=ix[x]+(ix[x]+1<(int)width);fx[x]=u-ix[x];
        }
        for(int y=top;y<bottom;y++){
            float v=fminf(height-1,fmaxf(0,a[5]+(y-a[1])*dv-(linear?0.5f:0)));
            int iy=(int)v,ny=iy+(iy+1<(int)height);
            const uint32_t *r=src+iy*(src_pitch/4), *n=src+ny*(src_pitch/4);
            for(int x=left;x<right;x++){
                uint32_t value=r[ix[x]];
                if(linear)value=mix_texels(mix_texels(value,r[nx[x]],fx[x]),
                    mix_texels(n[ix[x]],n[nx[x]],fx[x]),v-iy);
                dst[y*(dst_pitch/4)+x]=0xff000000u|value;
            }
        }
    }
    /* Log a few content changes so a device log distinguishes a moving
     * movie from repeated draws of its first texture. */
    if (state.movie_changes < 120) {
        uint32_t hash=2166136261u;
        for (unsigned y=0;y<height;y+=16)
            for (unsigned x=0;x<width;x+=16)
                hash=(hash^(dst[y*(dst_pitch/4)+x]&0xffffffu))*16777619u;
        if (!state.movie_frames || hash!=state.movie_hash) {
            state.movie_hash=hash;
            ++state.movie_changes;
            if (state.movie_changes==30 || state.movie_changes==120) {
                char line[96];
                snprintf(line,sizeof(line),"Movie content changes=%u draws=%u",state.movie_changes,state.movie_frames+1);
                ngb_kernel_log(line);
            }
        }
    }
    if (!state.movie_frames++) ngb_kernel_log("First decoded movie frame drawn");
#ifndef __SWITCH__
    char message[80];
    snprintf(message,sizeof(message),"PGRAPH decoded movie frame drawn physical=%08x",m[0x210/4]);
    ngb_kernel_log(message);
#endif
}

/* The title-to-menu transition draws a screen-aligned diffuse quad. */
struct diffuse_vertex { float x, y, z, w; uint32_t color; };
static void draw_diffuse_rect(int has_uv)
{
    struct diffuse_vertex v[4];
    const uint32_t *m = state.methods;
    unsigned width = m[0x200/4] >> 16, height = m[0x204/4] >> 16;
    unsigned pitch = m[0x20c/4] & 65535;
    if (!width || !height || width > 2048 || height > 2048 || pitch % 4 || pitch < width*4 ||
        m[0x208/4] != 0x128 || m[0xac0/4] != 0x04200000 || m[0x260/4] != 0x14200000 ||
        m[0x288/4] != 12 || m[0x28c/4] != 0x1c80 || !m[0x304/4] ||
        m[0x344/4] != 0x302 || m[0x348/4] != 0x303 || m[0x350/4] != 0x8006 ||
        m[0x358/4] != 0x01010101 || m[0x300/4] || m[0x30c/4])
        ngb_stop("unsupported diffuse rectangle state", m[0xac0/4]);
    for (unsigned i = 0; i < 16; ++i) {
        unsigned expected = i == 0 ? 0x42 : i == 3 ? 0x40 : has_uv && i == 9 ? 0x22 : 2;
        if ((m[0x1760/4+i] & 255) != expected) ngb_stop("unsupported diffuse vertex format", i);
    }
    for (unsigned i=0;i<4;i++) memcpy(&v[i],state.inline_words+i*(has_uv?7:5),sizeof(v[i]));
    int uniform=1;
    for (unsigned i=0;i<4;i++) {
        if (!isfinite(v[i].x) || !isfinite(v[i].y) || fabsf(v[i].x)>32768 ||
            fabsf(v[i].y)>32768 || v[i].z!=0 || v[i].w!=1)
            ngb_stop("unsupported diffuse vertex coordinates",i);
        uniform &= v[i].x==v[i&1].x && v[i].y==v[i&2].y && v[i].color==v[0].color;
    }
    if (!uniform || v[1].x<v[0].x || v[2].y<v[0].y) {
        uint32_t *dst=draw_surface(NV097_SET_CONTEXT_DMA_COLOR,m[0x210/4],(height-1)*pitch+width*4,CPU_TARGET);
        for (unsigned tri=0;tri<2;tri++) {
            const struct diffuse_vertex *a=&v[tri],*b=&v[tri+1],*c=&v[tri+2];
            float area=(b->x-a->x)*(c->y-a->y)-(b->y-a->y)*(c->x-a->x);
            if (!area) continue;
            if (area<0) { const struct diffuse_vertex *tmp=b;b=c;c=tmp;area=-area; }
            int x0=fmaxf(0,ceilf(fminf(a->x,fminf(b->x,c->x)))), x1=fminf(width-1,floorf(fmaxf(a->x,fmaxf(b->x,c->x))));
            int y0=fmaxf(0,ceilf(fminf(a->y,fminf(b->y,c->y)))), y1=fminf(height-1,floorf(fmaxf(a->y,fmaxf(b->y,c->y))));
            const struct diffuse_vertex *from[]={b,c,a},*to[]={c,a,b};
            float dx[3],dy[3]; bool inclusive[3];
            for (int k=0;k<3;k++) {
                dx[k]=to[k]->x-from[k]->x;dy[k]=to[k]->y-from[k]->y;
                inclusive[k]=dy[k]<0 || (!dy[k] && dx[k]>0);
            }
            for (int y=y0;y<=y1;y++) for (int x=x0;x<=x1;x++) {
                float e[3]; bool inside=true;
                for (int k=0;k<3;k++) {
                    e[k]=dx[k]*(y-from[k]->y)-dy[k]*(x-from[k]->x);
                    inside &= e[k]>0 || (e[k]==0 && inclusive[k]);
                }
                if (!inside) continue;
                uint32_t color=0;
                for(unsigned k=0;k<32;k+=8) {
                    float v0=(a->color>>k)&255, v1=(b->color>>k)&255, v2=(c->color>>k)&255;
                    color|=(uint32_t)fminf(255,fmaxf(0,(v0*e[0]+v1*e[1]+v2*e[2])/area+0.5f))<<k;
                }
                uint32_t *pixel=&dst[y*(pitch/4)+x];*pixel=blend_sprite(*pixel,color,0);
            }
        }
        return;
    }
    unsigned alpha = v[0].color >> 24;
    if (!alpha) return;
    int x0 = fminf(width, fmaxf(0, ceilf(v[0].x))), x1 = fminf(width, fmaxf(0, ceilf(v[1].x)));
    int y0 = fminf(height, fmaxf(0, ceilf(v[0].y))), y1 = fminf(height, fmaxf(0, ceilf(v[2].y)));
    uint32_t *dst = draw_surface(NV097_SET_CONTEXT_DMA_COLOR, m[0x210/4], (height-1)*pitch + width*4, CPU_TARGET);
    for (int y = y0; y < y1; ++y) {
        uint32_t *row = dst + y*(pitch/4);
        for (int x = x0; x < x1; ++x)
            row[x] = alpha == 255 ? v[0].color : blend_sprite(row[x],v[0].color,0);
    }
}

/* The story transition first captures its front buffer as a swizzled
 * A8R8G8B8 texture, then stretches it back onto a pitched render target. */
static void draw_transition_copy(const struct screen_vertex v[4], unsigned w, unsigned h, uint32_t tf)
{
    const uint32_t *m=state.methods;
    unsigned tw=1u<<((tf>>20)&15), th=1u<<((tf>>24)&15);
    unsigned pitch=m[0x20c/4]&65535;
    if (!w || !h || w>2048 || h>2048 || tw>2048 || th>2048 || (pitch&3) || pitch<w*4 ||
        m[0x208/4]!=0x128 || (tf&3)!=1 || m[0xac0/4]!=0x08040000 || m[0x260/4]!=0x18140000 ||
        m[0x288/4]!=12 || m[0x28c/4]!=0x1c80 || m[0x300/4] || m[0x30c/4] ||
        m[0x350/4]!=0x8006 || m[0x344/4]!=0x8003 || m[0x348/4]!=0x8004 ||
        m[0x358/4]!=0x01010101 || m[0x1b14/4]!=0x02022000 || m[0x1b08/4]!=0x10303)
        ngb_stop("unsupported transition copy state",tf);
    for (unsigned i=0;i<4;i++) {
        if (!isfinite(v[i].x) || !isfinite(v[i].y) || !isfinite(v[i].u) || !isfinite(v[i].v) ||
            v[i].x!=v[i&1].x || v[i].y!=v[i&2].y || v[i].u!=v[i&1].u || v[i].v!=v[i&2].v ||
            v[i].z!=0 || v[i].w!=1 || v[i].color!=v[0].color)
            ngb_stop("unsupported transition copy geometry",i);
    }
    if (v[1].x<=v[0].x || v[2].y<=v[0].y) ngb_stop("unsupported transition copy orientation",tf);
    unsigned left=fminf(w,fmaxf(0,ceilf(v[0].x))),right=fminf(w,fmaxf(0,ceilf(v[1].x)));
    unsigned top=fminf(h,fmaxf(0,ceilf(v[0].y))),bottom=fminf(h,fmaxf(0,ceilf(v[2].y)));
    float du=(v[1].u-v[0].u)/(v[1].x-v[0].x),dv=(v[2].v-v[0].v)/(v[2].y-v[0].y);
    unsigned alpha=m[0x304/4] ? m[0x34c/4]>>24 : 255;
    if (!alpha) return;
    uint32_t *src=draw_surface(NV097_SET_CONTEXT_DMA_A,m[0x1b00/4],tw*th*4,TEXTURE_SOURCE);
    uint32_t *dst=draw_surface(NV097_SET_CONTEXT_DMA_COLOR,m[0x210/4],(h-1)*pitch+w*4,CPU_TARGET);
    unsigned mx,my;
    xbox_swizzle_masks(tw,th,&mx,&my);
    struct { unsigned l,r; float f; } cols[2048];
    for (unsigned x=left;x<right;x++) {
        float u=fminf(tw-1,fmaxf(0,(v[0].u+(x-v[0].x)*du)*tw-0.5f));
        unsigned l=(unsigned)u;
        cols[x].l=swizzle_deposit(l,mx); cols[x].r=swizzle_deposit(l+(l+1<tw),mx); cols[x].f=u-l;
    }
    for (unsigned y=top;y<bottom;y++) {
        float t=fminf(th-1,fmaxf(0,(v[0].v+(y-v[0].y)*dv)*th-0.5f));
        unsigned a=(unsigned)t, b=swizzle_deposit(a+(a+1<th),my);
        float f=t-a; a=swizzle_deposit(a,my);
        uint32_t *row=dst+y*(pitch/4);
        for (unsigned x=left;x<right;x++) {
            unsigned l=cols[x].l,r=cols[x].r;
            uint32_t c=mix_texels(mix_texels(src[a|l],src[a|r],cols[x].f),
                                  mix_texels(src[b|l],src[b|r],cols[x].f),f);
            if (v[0].color!=UINT32_MAX) {
                uint32_t tinted=0;
                for (unsigned k=0;k<32;k+=8)
                    tinted|=(((((c>>k)&255)*((v[0].color>>k)&255))+127)/255)<<k;
                c=tinted;
            }
            row[x]=alpha==255 ? c : mix_texels(row[x],c,alpha/255.f);
        }
    }
}

static void draw_strip(void)
{
    struct screen_vertex v[4];
    if (state.inline_count==24) {
        draw_movie_strip();
        return;
    }
    if (state.inline_count == 20) {
        draw_diffuse_rect(0);
        return;
    }
    if (state.inline_count != sizeof(v) / 4)
        ngb_stop("unsupported inline vertex count", state.inline_count);
    memcpy(v, state.inline_words, sizeof(v));
    uint32_t *m = state.methods;
    for (unsigned i = 0; i < 16; i++) {
        unsigned f = m[0x1760 / 4 + i] & 255;
        unsigned expected = i == 0 ? 0x42 : i == 3 ? 0x40 : i == 9 ? 0x22 : 2;
        if (f != expected)
            ngb_stop("unsupported inline vertex format", i << 16 | f);
    }
    unsigned width = m[0x200 / 4] >> 16, height = m[0x204 / 4] >> 16;
    unsigned sw = m[0x1b1c / 4] >> 16, sh = m[0x1b1c / 4] & 65535, pitch = m[0x1b10 / 4] >> 16;
    uint32_t fmt = m[0x208 / 4], tf = m[0x1b04 / 4];
#ifndef __SWITCH__
    if (getenv("NGB_DRAW_TRACE") || (getenv("NGB_STORY_TRACE") && fmt==0x128 &&
        ((tf>>8)&255)!=0x19 && ((tf>>8)&255)!=0x0b)) {
        fprintf(stderr,
                "strip dst=%ux%u fmt=%08x db=%08x pitch=%08x src=%ux%u pitch=%u tex=%08x addr=%08x "
                "blend=%x/%x/%08x al=%x icw=%x ai=%x fin=%x/%x texaddr=%x filter=%x\n",
                width, height, fmt, m[0x210 / 4], m[0x20c / 4], sw, sh, pitch, tf, m[0x1b00 / 4],
                m[0x344 / 4], m[0x348 / 4], m[0x34c / 4], m[0x300 / 4], m[0xac0 / 4], m[0x260 / 4],
                m[0x288 / 4], m[0x28c / 4], m[0x1b08 / 4], m[0x1b14 / 4]);
        for (unsigned i = 0; i < 4; i++)
            fprintf(stderr, "vertex %g %g %g %g %08x %g %g\n", v[i].x, v[i].y, v[i].z, v[i].w, v[i].color,
                    v[i].u, v[i].v);
    }
#endif
    /* The stage transition leaves UVs enabled for a diffuse-only fade.
     * This combiner reads the vertex color, not the texture (which can
     * even alias the current render target). */
    if (fmt==0x128 && m[0xac0/4]==0x04200000 && m[0x260/4]==0x14200000) {
        draw_diffuse_rect(1);
        return;
    }
    if (((tf >> 8) & 255) == 0x06 && fmt==0x128) {
        draw_transition_copy(v,width,height,tf);
        return;
    }
    if (((tf >> 8) & 255) == 0x19 || ((tf >> 8) & 255) == 0x0b) {
        draw_alpha_sprite(v, width, height, fmt, tf);
        return;
    }
    if (!width || !height || width > 2048 || height > 2048 || !sw || !sh || sh > 4096 || sw > 4096 ||
        pitch < 4 * sw || pitch % 4 || ((tf >> 8) & 255) != 0x12 || (tf & 3) != 1 || (fmt & 0xf0f) != 0x208 ||
        (1u << ((fmt >> 16) & 15)) != width || (1u << ((fmt >> 24) & 15)) != height)
        ngb_stop("unsupported textured strip surfaces", fmt);
    if (m[0x1e60 / 4] != 1 || m[0xac0 / 4] != 0x2008 || m[0x260 / 4] != 0x18140000 || m[0x288 / 4] != 12 ||
        m[0x28c / 4] != 0x1c80 || m[0x344 / 4] != 0x8003 || m[0x348 / 4] != 0x8004 ||
        m[0x34c / 4] != UINT32_MAX || m[0x30c / 4] || m[0x300 / 4])
        ngb_stop("unsupported textured strip combiner", m[0xac0 / 4]);
    for (unsigned i = 0; i < 4; i++) {
        float x = (i & 1) ? width - 0.5f : -0.5f, y = (i & 2) ? height - 0.5f : -0.5f;
        if (v[i].x != x || v[i].y != y || v[i].z != 0 || v[i].w != 1 || v[i].color != UINT32_MAX ||
            v[i].u != ((i & 1) ? sw : 0) || v[i].v != ((i & 2) ? sh : 0))
            ngb_stop("unsupported screen-space strip geometry", i);
    }
    uint32_t *src = draw_surface(NV097_SET_CONTEXT_DMA_A, m[0x1b00 / 4], (sh - 1) * pitch + sw * 4, TEXTURE_SOURCE);
    uint32_t *dst = draw_surface(NV097_SET_CONTEXT_DMA_COLOR, m[0x210 / 4], width * height * 4, CPU_TARGET);
    uint32_t mx, my;
    xbox_swizzle_masks(width, height, &mx, &my);
    struct { unsigned left, right, dest; float fraction; } columns[2048];
    for (unsigned x = 0; x < width; x++) {
        float sx = fmaxf(0, ((x + 0.5f) * sw / width) - 0.5f);
        unsigned left = (unsigned)sx;
        columns[x].left = left;
        columns[x].right = left + 1 < sw ? left + 1 : left;
        columns[x].fraction = sx - left;
        columns[x].dest = swizzle_deposit(x, mx);
    }
    for (unsigned y = 0; y < height; y++) {
        float sy = fmaxf(0, ((y + 0.5f) * sh / height) - 0.5f);
        unsigned y0 = (unsigned)sy, y1 = y0 + 1 < sh ? y0 + 1 : y0;
        const uint32_t *top = src + y0 * (pitch/4), *bottom = src + y1 * (pitch/4);
        unsigned row = swizzle_deposit(y, my);
        for (unsigned x = 0; x < width; x++) {
            unsigned left = columns[x].left, right = columns[x].right;
            uint32_t a = mix_texels(top[left], top[right], columns[x].fraction);
            uint32_t b = mix_texels(bottom[left], bottom[right], columns[x].fraction);
            dst[row | columns[x].dest] = mix_texels(a, b, sy - y0);
        }
    }
    ngb_kernel_log("PGRAPH textured strip completed in guest render target");
}
