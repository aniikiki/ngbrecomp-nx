typedef struct {
    unsigned start, end, id;
    char command[6];
} PrologueCue;

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
    PrologueCue cue[128];
    unsigned cues;
    const PrologueCue *offered;
    bool accepted;
    uint32_t audio_origin, caption_frame;
    /* A converted frame is either in the title's texture or in our CPU buffer. */
    uint32_t *pixels;
    bool guest_textures;
} seq;

#ifdef NGB_DIRECT3D
/* sub_0031DEE0 creates these two D3D textures. sub_0031DA50 binds the
 * current slot and draws the movie quad before the game's subtitles. */
static uint32_t prologue_texture(unsigned slot) { return 0x9c2840 + slot * 20; }
#endif

static void seq_close(void)
{
    movie_audio_end();
    if (seq.file) fclose(seq.file);
    if (seq.parser) av_parser_close(seq.parser);
    sws_freeContext(seq.scale);
    av_frame_free(&seq.frame); av_packet_free(&seq.pkt);
    avcodec_free_context(&seq.codec);
    if (!seq.guest_textures) free(seq.pixels);
#ifdef NGB_DIRECT3D
    else if (seq.pixels) {
        /* The title can reuse the movie's memory immediately after a skip or EOF. */
        ngb_direct_wait_texture(prologue_texture(0));
        ngb_direct_wait_texture(prologue_texture(1));
    }
#endif
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
#ifdef NGB_DIRECT3D
    uint32_t *slot=NULL, next=0;
    if (seq.guest_textures) {
        slot=(uint32_t *)ngb_guest_pointer(0x9c258c,sizeof(*slot));
        if (*slot>1) return 0;
        next=*slot^1;
        dest[0]=ngb_direct_lock_prologue_texture(prologue_texture(next),720,480,&strides[0]);
        if (!dest[0]) return 0;
    }
#endif
    if (sws_scale(seq.scale,(const uint8_t *const *)seq.frame->data,seq.frame->linesize,
                  0,480,dest,strides)!=480) return 0;
#ifdef NGB_DIRECT3D
    if (slot) {
        /* Retail's decoder normally supplies texel coordinates along with
         * the picture. Keep the title's aspect-specific screen positions. */
        float (*quad)[6]=(float (*)[6])ngb_guest_pointer(0x9c2598,4*6*sizeof(float));
        for (unsigned i=0;i<4;i++) {
            quad[i][4]=(i&1)?720.0f:0.0f;
            quad[i][5]=(i&2)?480.0f:0.0f;
        }
        seq.pixels=(uint32_t *)dest[0];
        *slot=next;
    }
#endif
    return 1;
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
    /* The retail movie command reader (0019A950) selects MA for English
     * and MJ for Japanese. Their cues may overlap and have different lengths. */
    uint32_t language = *(const uint32_t *)ngb_guest_pointer(0xdb9890, 4);
    static const char tracks[] = {'J', 'A'};
    char track = language < sizeof tracks ? tracks[language] : 0;
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
        if(!tag_field(tags+pos,end-pos,"CONTENT",&n) || n>64 || tags[pos+16+n-1] ||
           seq.cues>=sizeof seq.cue/sizeof seq.cue[0] || pos+16+n!=end)return 0;
        /* Accept only the retail comma-separated M-language-number commands. */
        for(unsigned j=0;j+1<n;j++){
            unsigned c=tags[pos+16+j], k=j%6;
            if((!k && c!='M') || (k==1 && (c<'A'||c>'Z')) || (k>=2&&k<=4&&(c<'0'||c>'9')) ||
               (k==5&&c!=','))return 0;
        }
        if(n%6)return 0;
        PrologueCue *cue = &seq.cue[seq.cues++];
        cue->start = start;
        cue->end = start + duration;
        for (unsigned j = 0; j < n; j += 6) {
            const uint8_t *command = tags + pos + 16 + j;
            if (command[1] != track) continue;
            memcpy(cue->command, command, 5);
            cue->command[5] = 0;
            cue->id = (command[2] - '0') * 100 + (command[3] - '0') * 10 + (command[4] - '0');
            break;
        }
        i=end-1;
    }
    return known_unit && seq.cues && fseek(seq.file,0,SEEK_SET)==0;
}

static unsigned seq_caption_frame(void)
{
    NgbMoviePcmPosition pcm = ngb_pcm_movie_position();
    uint32_t played = pcm.read - seq.audio_origin;
    unsigned frame = seq.count - 1;
    /* The 48 kHz mixer excludes silence inserted during an underrun. Use the
     * picture clock when no audio is being consumed or samples were dropped. */
    if (played && played <= adx.output_frames && pcm.written - seq.audio_origin == adx.output_frames &&
        !(adx.disabled && adx.remaining))
        frame = (uint64_t)played * 29970 / 48000000;
    if (frame > seq.caption_frame) seq.caption_frame = frame;
    return seq.caption_frame;
}

static void seq_caption_age(const PrologueCue *cue, unsigned time)
{
    /* Retail starts fading out when the age equals fade-in plus hold.
     * Keep its hold clock on the movie timeline even if a picture is polled
     * twice or skipped. Once the fade has started the title owns it. */
    const uint16_t *timing = (const uint16_t *)ngb_guest_pointer(0x434458 + cue->id * 8, 8);
    unsigned ticks = (*(const uint8_t *)ngb_guest_pointer(0x9776a8, 1) & 0x40) ? 2 : 1;
    unsigned fade = (timing[1] + timing[2]) * ticks;
    uint32_t *age = (uint32_t *)ngb_guest_pointer(0x8fa9b8, 4);
    if (*age <= fade) {
        unsigned elapsed = (time - cue->start) * ticks / 1000;
        *age = elapsed < fade ? elapsed : fade;
    }
}

enum { CAPTION_READY = 1, CAPTION_RETIRE = 2 };

int ngb_prologue_caption(uint32_t stack)
{
    if (!seq.pixels) return -1;
    uint32_t args[4];
    memcpy(args, (void *)ngb_guest_pointer(stack + 4, sizeof args), sizeof args);
    if (args[1] != 0x9c2600 || args[2] != 256 || args[3] != 0x9c271c) return -1;
    char *dst = (char *)ngb_guest_pointer(args[1], 256);
    dst[0] = 0;
    memset((void *)ngb_guest_pointer(args[3], 20), 0, 20);
    /* Slot zero of the retail subtitle system: live, slot, flags, kind, ID.
     * An offered command can be polled before the game has accepted it. */
    const uint16_t *slot = (const uint16_t *)ngb_guest_pointer(0x8fa9bc, 10);
    bool visible = seq.offered && slot[0] && slot[3] == 6 && slot[4] == seq.offered->id;
    if (visible) seq.accepted = true;

    unsigned time = seq_caption_frame() * 1000;
    const PrologueCue *next = NULL;
    for (unsigned i = 0; i < seq.cues; ++i) {
        const PrologueCue *cue = &seq.cue[i];
        if (cue->command[0] && time >= cue->start && time <= cue->end) {
            next = cue;
            break;
        }
    }
    if (visible && next == seq.offered) seq_caption_age(next, time);
    int result = visible && next != seq.offered ? CAPTION_RETIRE : 0;
    if (next != seq.offered) {
        seq.offered = next;
        seq.accepted = false;
    }
    if (next && !seq.accepted) {
        memcpy(dst, next->command, sizeof next->command);
        result |= CAPTION_READY;
    }
    return result;
}
int ngb_prologue_begin(void)
{
    if (!guest_prologue || seq.file) return 0;
    seq.file=ngb_open_disc_movie("ninja_gaiden.sfd");
    if (!seq.file) return 0;
    seq.audio_origin=ngb_pcm_movie_position().written;
    setvbuf(seq.file,NULL,_IOFBF,128*1024);
    const AVCodec *decoder=avcodec_find_decoder(AV_CODEC_ID_MPEG1VIDEO);
    if (decoder && (seq.codec=avcodec_alloc_context3(decoder))) seq.codec->thread_count=1;
    seq.parser=av_parser_init(AV_CODEC_ID_MPEG1VIDEO);
    seq.frame=av_frame_alloc(); seq.pkt=av_packet_alloc();
#ifdef NGB_DIRECT3D
    seq.guest_textures=ngb_d3d_native_enabled();
#endif
    if (!seq.guest_textures) {
        seq.pixels=malloc(720*480*4);
        if (!seq.pixels) {seq_close();return 0;}
    }
    seq.scale=sws_getContext(720,480,AV_PIX_FMT_YUV420P,720,480,AV_PIX_FMT_BGRA,SWS_POINT,NULL,NULL,NULL);
    if (!seq_cues() || !seq.codec || !seq.parser || !seq.frame || !seq.pkt || !seq.scale ||
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
    uint64_t now = ngb_elapsed_ns();
    if (!seq.start) {
        seq.start = now;
        return 1; /* The first picture was decoded when the movie opened. */
    }
    /* Pace picture changes at the encoded frame rate. */
    uint64_t next = seq.start + seq.count * seq.period;
    if (now < next) {
        ngb_graphics_wait_until(next);
        if (ngb_stop_requested() || selection_edge != ngb_movie_skip_edges()) return 0;
        now = ngb_elapsed_ns();
    }
    uint64_t target = 1 + (now - seq.start) / seq.period;
    do {
        if (seq_next() != 1) return 0;
    } while (seq.count < target);
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
        "stp x29,x30,[sp,#-16]!\nmov w0,w22\nbl ngb_prologue_caption\n"
        "tbnz w0,#31,3f\ntbz w0,#1,1f\n"
        /* The old caption can still own its glyphs when the movie advances.
         * Let the original slot destructor release them and pop the guest
         * return address. Preserve the query result and guest ECX / EDX. */
        "stp x20,x21,[sp,#-32]!\nstr w0,[sp,#16]\nmov w19,wzr\nbl " STR(NGB_PROLOGUE_CLEAR) "\n"
        "ldr w0,[sp,#16]\nldp x20,x21,[sp],#32\nb 2f\n"
        "1: add w22,w22,#4\n2: and w19,w0,#1\nldp x29,x30,[sp],#16\nret\n"
        "3: ldp x29,x30,[sp],#16\nb __real_" STR(NGB_PROLOGUE_CAPTION) "\n");
#endif
