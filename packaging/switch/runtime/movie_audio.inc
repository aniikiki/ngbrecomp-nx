// Native Sofdec playback bypasses the guest decoder. Audio PES payloads
// concatenate into a CRI ADX stream; sectors need not end on a codec block.
#include "audio_output.h"
static struct {
    AVCodecContext *codec;
    AVFrame *frame;
    unsigned used,channels,rate,phase,disabled;
    uint32_t remaining, output_frames;
    uint8_t bytes[4096+AV_INPUT_BUFFER_PADDING_SIZE];
    int prev[2],have_prev;
} adx;
static void movie_audio_end(void){
    avcodec_free_context(&adx.codec);av_frame_free(&adx.frame);
    memset(&adx,0,sizeof adx);ngb_pcm_flush(1);
}
static void movie_audio_samples(void){
    AVFrame *f=adx.frame;
    if(f->format!=AV_SAMPLE_FMT_S16P)return;
    int16_t pcm[512*2];unsigned count=0;
    const int16_t *left=(const int16_t*)f->extended_data[0];
    const int16_t *right=adx.channels==1?left:(const int16_t*)f->extended_data[1];
    for(int i=0;i<f->nb_samples && adx.remaining;i++,adx.remaining--){
        int cur[2]={left[i],right[i]};
        if(!adx.have_prev){memcpy(adx.prev,cur,sizeof cur);adx.have_prev=1;}
        while(adx.phase<48000){
            for(unsigned c=0;c<2;c++)pcm[count*2+c]=adx.prev[c]+(int)((int64_t)(cur[c]-adx.prev[c])*adx.phase/48000);
            if(++count==512){ngb_pcm_submit(1,pcm,count);adx.output_frames+=count;count=0;}
            adx.phase+=adx.rate;
        }
        adx.phase-=48000;memcpy(adx.prev,cur,sizeof cur);
    }
    if(count){ngb_pcm_submit(1,pcm,count);adx.output_frames+=count;}
}
static void movie_audio_packet(const uint8_t *src,unsigned bytes){
    if(adx.disabled || bytes>4096-adx.used)return;
    uint8_t *p=adx.bytes;memcpy(p+adx.used,src,bytes);adx.used+=bytes;
    if(!adx.codec){
        if(adx.used<20)return;
        unsigned hdr=4+(p[2]<<8)+p[3];
        adx.channels=p[7];adx.rate=((uint32_t)p[8]<<24)|(p[9]<<16)|(p[10]<<8)|p[11];
        adx.remaining=((uint32_t)p[12]<<24)|(p[13]<<16)|(p[14]<<8)|p[15];
        if(p[0]!=0x80 || p[1] || p[4]!=3 || p[5]!=18 || p[6]!=4 || hdr<20 || hdr>2048 ||
           !adx.channels || adx.channels>2 || adx.rate<8000 || adx.rate>48000)goto fail;
        if(adx.used<hdr)return;
        const AVCodec *dec=avcodec_find_decoder(AV_CODEC_ID_ADPCM_ADX);
        if(!dec || !(adx.codec=avcodec_alloc_context3(dec)) || !(adx.frame=av_frame_alloc()))goto fail;
        adx.codec->extradata=av_mallocz(hdr+AV_INPUT_BUFFER_PADDING_SIZE);
        if(!adx.codec->extradata)goto fail;
        memcpy(adx.codec->extradata,p,hdr);adx.codec->extradata_size=(int)hdr;
        if(avcodec_open2(adx.codec,dec,NULL)<0)goto fail;
        adx.used-=hdr;memmove(p,p+hdr,adx.used);
    }
    unsigned block=18*adx.channels,size=adx.used/block*block;
    unsigned blocks=(adx.remaining+31ull)/32;
    if(size/block>blocks)size=blocks*block;
    if(size){
        // Give FFmpeg an owned packet with zero padding independent of the unconsumed tail.
        AVPacket *pkt=av_packet_alloc();if(!pkt || av_new_packet(pkt,(int)size)<0){av_packet_free(&pkt);goto fail;}
        memcpy(pkt->data,p,size);int rc=avcodec_send_packet(adx.codec,pkt);av_packet_free(&pkt);if(rc<0)goto fail;
        while((rc=avcodec_receive_frame(adx.codec,adx.frame))==0)movie_audio_samples();
        if(rc!=AVERROR(EAGAIN) && rc!=AVERROR_EOF)goto fail;
        adx.used-=size;memmove(p,p+size,adx.used);
    }
    if(!adx.remaining)adx.disabled=1;
    return;
fail:
    adx.disabled=1;ngb_kernel_log("Movie ADX soundtrack unavailable");
}
