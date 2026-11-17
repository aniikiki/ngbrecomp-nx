/* Guest worker only. Pull a frame on demand; the game's display loop still
 * composites its own captions and advances the narration between polls. */
static struct {
    FILE *file;
    AVCodecParserContext *parser;
    AVCodecContext *codec;
    AVPacket *pkt;
    AVFrame *frame;
    struct SwsContext *scale;
    uint8_t sector[2048+AV_INPUT_BUFFER_PADDING_SIZE], *data;
    int size, drain, end;
    unsigned count;
    uint64_t start, period;
    struct {unsigned start,end; char text[64];} cue[128];
    unsigned cues;
    uint32_t *pixels;
} seq;

static void seq_close(void)
{
    movie_audio_end();
    if (seq.file) fclose(seq.file);
    if (seq.parser) av_parser_close(seq.parser);
    sws_freeContext(seq.scale);
    av_frame_free(&seq.frame); av_packet_free(&seq.pkt);
    avcodec_free_context(&seq.codec); free(seq.pixels);
    memset(&seq,0,sizeof(seq));
}

static int seq_next(void)
{
    for (;;) {
        int rc=avcodec_receive_frame(seq.codec,seq.frame);
        if (!rc) { ++seq.count; return 1; }
        if (rc==AVERROR_EOF) return 0;
        if (rc!=AVERROR(EAGAIN) || seq.drain || ngb_stop_requested()) return -1;
        if (!seq.size && !seq.end) {
            seq.size=next_packet(seq.file,seq.sector,&seq.data);
            if (seq.size<0) return -1;
            seq.end=seq.size==0;
        }
        int used=av_parser_parse2(seq.parser,seq.codec,&seq.pkt->data,&seq.pkt->size,
            seq.end?NULL:seq.data,seq.size,AV_NOPTS_VALUE,AV_NOPTS_VALUE,0);
        if (used<0 || (!used && !seq.pkt->size && !seq.end)) return -1;
        if (used) {seq.data+=used;seq.size-=used;}
        if (seq.pkt->size) {if(avcodec_send_packet(seq.codec,seq.pkt)<0)return -1;}
        else if (seq.end) {seq.drain=1;if(avcodec_send_packet(seq.codec,NULL)<0)return -1;}
    }
}

static int seq_convert(void)
{
    if (seq.frame->width!=720 || seq.frame->height!=480 || seq.frame->format!=AV_PIX_FMT_YUV420P) return 0;
    uint8_t *dest[4]={(uint8_t *)seq.pixels};
    int strides[4]={720*4};
    return sws_scale(seq.scale,(const uint8_t *const *)seq.frame->data,seq.frame->linesize,
                     0,480,dest,strides)==480;
}

/* Concatenate the Sofdec private packets: a TIMEDAT record can straddle a
 * sector. Each CRI tag has an 8-byte name and an ASCII hex payload length. */
static int tag_field(const uint8_t *p,size_t available,const char *key,unsigned *bytes)
{
    if(available<16 || memcmp(p,key,strlen(key)+1))return 0;
    unsigned n=0;
    for(unsigned j=8;j<15;j++){
        unsigned c=p[j];
        if(c>='0' && c<='9')c-='0';
        else if(c>='a' && c<='f')c=c-'a'+10;
        else return 0;
        n=n*16+c;
    }
    if(p[15] || !n || n>available-16)return 0;
    *bytes=n;return 1;
}
static int cue_number(const uint8_t *p,unsigned n,unsigned *out)
{
    unsigned x=0;
    if(n<2 || n>9 || p[n-1])return 0;
    for(unsigned j=0;j<n-1;j++){
        if(p[j]<'0' || p[j]>'9')return 0;
        x=x*10+p[j]-'0';
    }
    *out=x;return 1;
}
static int seq_cues(void)
{
    uint8_t tags[16384],block[2048];size_t size=0;
    for(unsigned i=0;i<32 && fread(block,1,sizeof block,seq.file)==sizeof block;i++){
        if(block[15]==0xe0)break;
        if(block[15]!=0xbf)continue;
        unsigned n=block[16]*256u+block[17];
        if(n>2030 || n>sizeof(tags)-size)return 0;
        memcpy(tags+size,block+18,n);size+=n;
    }
    int known_unit=0;
    for(size_t i=0;i+16<=size;i++) {
        unsigned n,start,duration;
        if(tag_field(tags+i,size-i,"TUNIT",&n) && cue_number(tags+i+16,n,&start))
            known_unit=start==29970;
        if(!tag_field(tags+i,size-i,"TIMEDAT",&n))continue;
        size_t pos=i+16,end=pos+n;
        if(!tag_field(tags+pos,end-pos,"INTIME",&n) || !cue_number(tags+pos+16,n,&start))return 0;
        pos+=16+n;
        if(!tag_field(tags+pos,end-pos,"DURTIME",&n) || !cue_number(tags+pos+16,n,&duration))return 0;
        pos+=16+n;
        if(!tag_field(tags+pos,end-pos,"CONTENT",&n) || n>sizeof seq.cue[0].text || tags[pos+16+n-1] ||
           seq.cues>=sizeof seq.cue/sizeof seq.cue[0] || pos+16+n!=end)return 0;
        /* Accept only the retail comma-separated M-language-number commands. */
        for(unsigned j=0;j+1<n;j++){
            unsigned c=tags[pos+16+j], k=j%6;
            if((!k && c!='M') || (k==1 && (c<'A'||c>'Z')) || (k>=2&&k<=4&&(c<'0'||c>'9')) ||
               (k==5&&c!=','))return 0;
        }
        if(n%6)return 0;
        seq.cue[seq.cues].start=start;seq.cue[seq.cues].end=start+duration;
        memcpy(seq.cue[seq.cues++].text,tags+pos+16,n);
        i=end-1;
    }
    return known_unit && seq.cues && fseek(seq.file,0,SEEK_SET)==0;
}
int ngb_prologue_caption(uint32_t stack)
{
    if (!seq.pixels) return -1;
    uint32_t args[4]; memcpy(args,(void *)ngb_guest_pointer(stack+4,16),16);
    if(args[1]!=0x9c2600 || args[2]!=256 || args[3]!=0x9c271c)return -1;
    char *dst=(char *)ngb_guest_pointer(args[1],256);size_t used=0;
    memset((void *)ngb_guest_pointer(args[3],20),0,20);
    unsigned time=(seq.count-1)*1000;
    for(unsigned i=0;i<seq.cues;i++)if(time>=seq.cue[i].start && time<=seq.cue[i].end){
        size_t n=strlen(seq.cue[i].text);
        if(used+n+1>=256)break;
        if(used)dst[used++]=',';
        memcpy(dst+used,seq.cue[i].text,n);used+=n;
    }
    memset(dst+used,0,256-used);
    return used!=0;
}
int ngb_prologue_begin(void)
{
    if (!guest_prologue || seq.file) return 0;
    seq.file=ngb_open_disc_movie("ninja_gaiden.sfd");
    if (!seq.file) return 0;
    setvbuf(seq.file,NULL,_IOFBF,128*1024);
    const AVCodec *decoder=avcodec_find_decoder(AV_CODEC_ID_MPEG1VIDEO);
    if (decoder && (seq.codec=avcodec_alloc_context3(decoder))) seq.codec->thread_count=1;
    seq.parser=av_parser_init(AV_CODEC_ID_MPEG1VIDEO);
    seq.frame=av_frame_alloc(); seq.pkt=av_packet_alloc(); seq.pixels=malloc(720*480*4);
    seq.scale=sws_getContext(720,480,AV_PIX_FMT_YUV420P,720,480,AV_PIX_FMT_BGRA,SWS_POINT,NULL,NULL,NULL);
    if (!seq_cues() || !seq.codec || !seq.parser || !seq.frame || !seq.pkt || !seq.pixels || !seq.scale ||
        avcodec_open2(seq.codec,decoder,NULL)<0 || seq_next()!=1 || !seq_convert()) {
        seq_close();return 0;
    }
    AVRational rate=seq.codec->framerate;
    if (rate.num<=0 || rate.den<=0 || av_q2d(rate)<29 || av_q2d(rate)>31){seq_close();return 0;}
    seq.period=av_rescale(1000000000,rate.den,rate.num);
    return 1;
}

const uint32_t *ngb_prologue_pixels(void) {return seq.pixels;}

static int seq_playing(void)
{
    if (!seq.start) seq.start=ngb_elapsed_ns();
    unsigned target=1+(ngb_elapsed_ns()-seq.start)/seq.period;
    if (target<=seq.count) return 1;
    do {if(seq_next()!=1)return 0;} while (seq.count<target);
    return seq_convert();
}

#ifdef NGB_PROLOGUE_START
/* The lifted guest's cdecl return pops one Xbox return address (w22).
 * Fall through to the retail start call if we couldn't prime the stream. */
#define STR_(x) #x
#define STR(x) STR_(x)
__asm__(".text\n.p2align 2\n.global __wrap_" STR(NGB_PROLOGUE_START) "\n"
        "__wrap_" STR(NGB_PROLOGUE_START) ":\n"
        "stp x29,x30,[sp,#-16]!\nbl ngb_prologue_begin\nldp x29,x30,[sp],#16\n"
        "cbz w0,1f\nadd w22,w22,#4\nmov w19,#0\nret\n1: b __real_" STR(NGB_PROLOGUE_START) "\n");
__asm__(".text\n.p2align 2\n.global __wrap_" STR(NGB_PROLOGUE_CAPTION) "\n"
        "__wrap_" STR(NGB_PROLOGUE_CAPTION) ":\n"
        "stp x29,x30,[sp,#-16]!\nmov w0,w22\nbl ngb_prologue_caption\nldp x29,x30,[sp],#16\n"
        "tbnz w0,#31,1f\nadd w22,w22,#4\nmov w19,w0\nret\n1: b __real_" STR(NGB_PROLOGUE_CAPTION) "\n");
#endif
