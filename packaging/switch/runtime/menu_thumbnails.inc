// The mission grid repeatedly scales subrects of a 1024-square indexed atlas.
// Cache filtered foreground pixels, never the framebuffer behind a preview.
enum { THUMB_W=144, THUMB_H=96, THUMB_TILES=128, THUMB_SLOTS=48 };
typedef struct {
    float sampling[8];
    unsigned w,h,count,valid,opaque;
    uint32_t palette[256],pixels[THUMB_W*THUMB_H];
    unsigned offsets[THUMB_TILES],tiles;
    uint8_t snapshot[THUMB_TILES][256];
} Thumb;
static Thumb thumbs[THUMB_SLOTS];
static unsigned next_thumb;

static Thumb *thumbnail(const struct screen_vertex v[4],const uint8_t *tex,const uint32_t *pal,
                       unsigned count,int x,int y,int w,int h,int *hit){
    if(w<=0 || h<=0 || w>THUMB_W || h>THUMB_H || w*h<4096)return NULL;
    // Keep the actual sampling coordinates relative to the clipped origin.
    // Integer translations reuse the same filtered pixels; subpixel moves,
    // clipping, UV changes and palette animation must still miss.
    const float sampling[]={x-v[0].x,y-v[0].y,v[1].x-v[0].x,v[2].y-v[0].y,
                            v[0].u,v[0].v,v[1].u,v[2].v};
    for(unsigned i=0;i<THUMB_SLOTS;i++){
        Thumb *t=thumbs+i;
        if(!t->valid || t->w!=(unsigned)w || t->h!=(unsigned)h || t->count!=count ||
           memcmp(t->sampling,sampling,sizeof sampling) || memcmp(t->palette,pal,count*4))continue;
        unsigned j=0;
        while(j<t->tiles && !memcmp(t->snapshot[j],tex+t->offsets[j],256))j++;
        if(j==t->tiles){*hit=1;return t;}
        t->valid=0;break;
    }
    // Bound every bilinear tap, including the neighbouring texel. Morton
    // layout stores each aligned 16x16 tile in exactly 256 adjacent bytes.
    int tmin[2],tmax[2];
    for(unsigned a=0;a<2;a++){
        float lo=a?v[0].y:v[0].x, hi=a?v[2].y:v[1].x;
        float uv=a?v[0].v:v[0].u, du=(a?v[2].v:v[1].u)-uv;
        int first=a?y:x,last=first+(a?h:w)-1;
        float p=(uv+((first-lo)/(hi-lo))*du)*1024-0.5f;
        float q=(uv+((last-lo)/(hi-lo))*du)*1024-0.5f;
        tmin[a]=(int)fminf(1023,fmaxf(0,fminf(p,q)-1))/16;
        tmax[a]=(int)fminf(1023,fmaxf(0,fmaxf(p,q)+2))/16;
    }
    if((tmax[0]-tmin[0]+1)*(tmax[1]-tmin[1]+1)>THUMB_TILES)return NULL;
    Thumb *t=&thumbs[next_thumb++%THUMB_SLOTS];t->valid=0;t->tiles=0;t->opaque=1;
    for(int j=tmin[1];j<=tmax[1];j++)for(int i=tmin[0];i<=tmax[0];i++){
        unsigned off=swizzle_spread(i*16)|(swizzle_spread(j*16)<<1);
        t->offsets[t->tiles]=off;memcpy(t->snapshot[t->tiles++],tex+off,256);
    }
    t->w=w;t->h=h;t->count=count;
    memcpy(t->sampling,sampling,sizeof sampling);memcpy(t->palette,pal,count*4);return t;
}

// The mission title strip stretches a small indexed texture across the
// screen. Cache its filtered foreground, including fractional edge coverage.
enum { STRIP_W=720, STRIP_H=64 };
static struct {
    uint32_t pixels[STRIP_W*STRIP_H],palette[256];
    uint8_t indices[256*64];
    float sampling[8];
    unsigned count,w,h;
    int valid,opaque;
} title_strip;

static int title_strip_hit(const struct screen_vertex *v,int x,int y,unsigned w,unsigned h,
                           const uint8_t *tex,const uint32_t *pal,unsigned count){
    float key[]={x-v[0].x,y-v[0].y,v[1].x-v[0].x,v[2].y-v[0].y,
                 v[0].u,v[0].v,v[1].u,v[2].v};
    if(title_strip.valid && w==title_strip.w && h==title_strip.h && count==title_strip.count &&
       !memcmp(key,title_strip.sampling,sizeof key) && !memcmp(pal,title_strip.palette,count*4) &&
       !memcmp(tex,title_strip.indices,sizeof title_strip.indices))return 1;
    title_strip.valid=0;title_strip.opaque=1;title_strip.w=w;title_strip.h=h;title_strip.count=count;
    memcpy(title_strip.sampling,key,sizeof key);memcpy(title_strip.palette,pal,count*4);
    memcpy(title_strip.indices,tex,sizeof title_strip.indices);return 0;
}
