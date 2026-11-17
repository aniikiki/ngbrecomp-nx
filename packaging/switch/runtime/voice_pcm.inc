// Read sample data through the voice scatter/gather table. A PCM frame or
// encoded ADPCM block may cross two non-adjacent guest pages.
#include "apu/adpcm_block.h"
enum { MIX_LIMIT=2048 };
static int32_t pcm_mix[MIX_LIMIT][2];
static uint16_t gain_table[4096];
static void init_levels(void){
    if(!gain_table[0])for(unsigned i=0;i<4095;i++)gain_table[i]=(uint16_t)lround(32768*pow(10.,-(double)i/1280));
}
typedef struct {uint32_t vpn;const uint8_t *page;} PcmPage;
static void source_page(PcmPage *cache,uint32_t vpn){
    if(cache->vpn!=vpn){
        cache->vpn=vpn;cache->page=NULL;
        uint64_t slot=(uint64_t)apu_config[NV_PAPU_VPSGEADDR/4]+8ull*cache->vpn;
        if(slot && slot+4<=0x8000000){
            uint32_t page;memcpy(&page,ngb_dma_pointer((uint32_t)slot,4),4);
            if(page && !(page&4095) && page<0x8000000)cache->page=ngb_dma_pointer(page,4096);
        }
    }
}
static void source_read(PcmPage *cache,uint32_t addr,void *dst,unsigned bytes){
    uint8_t *out=dst;
    while(bytes){
        unsigned off=addr&4095,n=4096-off;if(n>bytes)n=bytes;
        source_page(cache,addr>>12);
        if(cache->page)memcpy(out,cache->page+off,n);else memset(out,0,n);
        out+=n;bytes-=n;addr+=n;
    }
}
// Guest buffers and their DMA mappings can change between polls. Compare the
// current encoded bytes (not just the block address) before reusing samples.
typedef struct {
    unsigned bytes;
    uint8_t raw[72];
    int16_t samples[65*2];
} VoiceAdpcmBlock;
static VoiceAdpcmBlock adpcm_blocks[256];
static const int16_t *decode_voice_block(unsigned id,PcmPage *page,uint32_t addr,unsigned channels){
    VoiceAdpcmBlock *saved=&adpcm_blocks[id];
    uint8_t raw[72];unsigned bytes=36*channels;
    source_read(page,addr,raw,bytes);
    if(saved->bytes!=bytes || memcmp(saved->raw,raw,bytes)!=0){
        adpcm_decode_block(saved->samples,raw,bytes,channels);
        memcpy(saved->raw,raw,bytes);saved->bytes=bytes;
    }
    return saved->samples;
}
typedef struct {
    uint32_t fmt,bins,vol[3];
    uint64_t generation;
    int valid,gain[2][2];
    int16_t pitch;
    double rate;
} MixParams;
static MixParams mix_params[256];
static uint64_t gain_generation;
static double playback_rate(unsigned id,int16_t pitch){
    if(!pitch)return 1.0;
    MixParams *p=&mix_params[id];
    if(p->pitch!=pitch){p->pitch=pitch;p->rate=exp2(pitch/4096.0);}
    return p->rate;
}
static void update_gain(unsigned id,const uint32_t *v,unsigned fmt,unsigned channels){
    MixParams *params=&mix_params[id];
    const uint32_t *words=v+NV_PAVS_VOICE_TAR_VOLA/4;
    unsigned bins=v[NV_PAVS_VOICE_CFG_VBIN/4];
    if(params->valid && params->generation==gain_generation && params->fmt==fmt &&
       params->bins==bins && !memcmp(params->vol,words,sizeof params->vol))return;
    params->valid=1;params->generation=gain_generation;params->fmt=fmt;params->bins=bins;
    memcpy(params->vol,words,sizeof params->vol);
    int (*gain)[2]=params->gain;
    memset(gain,0,sizeof params->gain);
    unsigned vol[8]={0};
    for(unsigned i=0;i<3;i++){
        unsigned word=v[NV_PAVS_VOICE_TAR_VOLA/4+i];vol[2*i]=word>>4&4095;vol[2*i+1]=word>>20;
        vol[6]|=(word&15)<<(4*i);vol[7]|=(word>>16&15)<<(4*i);
    }
    for(unsigned b=0;b<8;b++){
        unsigned bin=(b>=6?fmt>>(5*(b-6)):bins>>(b<3?5*b:16+5*(b-3)))&31;
        if(id<64 && b<4)bin=(unsigned[]){6,8,7,9}[b];
        if(bin>9)continue; // effects sends are not speakers
        int level=gain_table[vol[b]]>>(voice_setup[(0x200+4*bin)/4]&7);
        unsigned ch=b%channels;
        if(bin==2 || bin==3){gain[0][ch]+=level/2;gain[1][ch]+=level/2;}
        else gain[bin==1 || bin==5 || bin==7 || bin==9][ch]+=level;
    }
}
static void mix_voice(unsigned id,const uint32_t *v,unsigned fmt,unsigned pos,unsigned end,unsigned loop,
                      double frac,double rate,unsigned n,uint64_t skipped){
    if(!n || !apu_config[NV_PAPU_VPSGEADDR/4] || (fmt&NV_PAVS_VOICE_CFG_FMT_MULTIPASS))return;
    unsigned channels=1+((fmt>>27)&1),stride=1+((fmt>>16)&31),type=fmt>>30,bits=(fmt>>28)&3;
    unsigned base=v[NV_PAVS_VOICE_CUR_PSL_START/4]&0xffffff;
    if(stride<channels)return;
    update_gain(id,v,fmt,channels);
    const int (*gain)[2]=mix_params[id].gain;
    if(!(gain[0][0]|gain[1][0]|gain[0][1]|gain[1][1]))return;
    PcmPage cache={.vpn=UINT32_MAX};unsigned last_block=UINT32_MAX;
    const int16_t *decoded=NULL;unsigned bytes=(unsigned[]){1,2,0,4}[type];
    double cursor=pos+frac+skipped*rate;
    // Read adjacent PCM16 frames together, including when the DMA pages
    // backing the voice are not contiguous. Stop each batch at a loop edge.
    if(type==1 && bits==1 && stride==channels && rate==1.0){
        uint64_t p=(uint64_t)cursor;
        for(unsigned i=0;i<n;){
            if(p>end){if(!(fmt&NV_PAVS_VOICE_CFG_FMT_LOOP))break;p=loop+(p-end-1)%(end-loop+1);}
            unsigned count=n-i;
            if(count>32)count=32;
            if(count>end-p+1)count=end-p+1;
            int16_t buf[32*2];
            source_read(&cache,base+(uint32_t)p*2*channels,buf,count*2*channels);
            for(unsigned j=0;j<count;j++){
                int l=buf[j*channels],r=channels==2?buf[2*j+1]:0;
                for(unsigned ear=0;ear<2;ear++)pcm_mix[i+j][ear]+=(int)(((int64_t)gain[ear][0]*l+(int64_t)gain[ear][1]*r)/32768);
            }
            i+=count;p+=count;
        }
        return;
    }
    // Gather variable-pitch PCM directly from a mapped page. Use the same
    // incremental double cursor as the scalar path (including after a wrap).
    if(type!=2 && rate!=1.0){
        unsigned step=bytes*stride,width=bytes*channels,i=0;
        while(i<n){
            uint64_t start=(uint64_t)cursor,p=start;
            if(p>end){if(!(fmt&NV_PAVS_VOICE_CFG_FMT_LOOP))break;p=loop+(p-end-1)%(end-loop+1);}
            uint32_t addr=base+(uint32_t)p*step;
            unsigned off=addr&4095;
            uint8_t split[8]={0};
            const uint8_t *src;
            unsigned span=0;
            if(off+width>4096){source_read(&cache,addr,split,width);src=split;}
            else{
                source_page(&cache,addr>>12);
                src=cache.page?cache.page+off:NULL;
                span=(4096-off-width)/step;
                if(span>end-p)span=end-p;
            }
            unsigned delta=0;
            do {
                int sample[2]={0};
                for(unsigned c=0;c<channels;c++){
                    uint32_t x=0;
                    if(src){
                        const uint8_t *q=src+delta*step+c*bytes;
                        if(bytes==1)x=*q;
                        else if(bytes==2){uint16_t u;memcpy(&u,q,2);x=u;}
                        else memcpy(&x,q,4);
                    }
                    sample[c]=bits==0?((int)(x&255)-128)*256:bits==1?(int16_t)x:
                              bits==2?(int32_t)(x<<8)>>16:(int32_t)x>>16;
                }
                for(unsigned ear=0;ear<2;ear++)pcm_mix[i][ear]+=(int)(((int64_t)gain[ear][0]*sample[0]+(int64_t)gain[ear][1]*sample[1])/32768);
                i++;cursor+=rate;
                uint64_t distance=(uint64_t)cursor-start;
                if(distance>span)break;
                delta=(unsigned)distance;
            }while(i<n);
        }
        return;
    }
    for(unsigned i=0;i<n;i++,cursor+=rate){
        uint64_t p=(uint64_t)cursor;
        if(p>end){if(!(fmt&NV_PAVS_VOICE_CFG_FMT_LOOP))break;p=loop+(p-end-1)%(end-loop+1);}
        int sample[2]={0};
        if(type==2){
            unsigned blk=p/64;
            if(blk!=last_block){
                decoded=decode_voice_block(id,&cache,base+blk*36*stride,channels);last_block=blk;
            }
            for(unsigned c=0;c<channels;c++)sample[c]=decoded[(p%64)*channels+c];
        }else{
            uint8_t raw[8];source_read(&cache,base+(uint32_t)p*bytes*stride,raw,bytes*channels);
            for(unsigned c=0;c<channels;c++){
                uint32_t x=0;memcpy(&x,raw+c*bytes,bytes);
                sample[c]=bits==0?((int)(x&255)-128)*256:bits==1?(int16_t)x:
                          bits==2?(int32_t)(x<<8)>>16:(int32_t)x>>16;
            }
        }
        for(unsigned ear=0;ear<2;ear++)pcm_mix[i][ear]+=(int)(((int64_t)gain[ear][0]*sample[0]+(int64_t)gain[ear][1]*sample[1])/32768);
    }
}
static void submit_mix(unsigned n){
    int16_t pcm[MIX_LIMIT*2];for(unsigned i=0;i<n;i++)for(unsigned c=0;c<2;c++)pcm[2*i+c]=pcm_clip(pcm_mix[i][c]);
    ngb_pcm_submit(0,pcm,n);
}
