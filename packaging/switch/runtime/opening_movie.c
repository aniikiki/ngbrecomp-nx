#define _POSIX_C_SOURCE 200809L
#include "runtime.h"
#include "scanout.h"
#include "files.h"
#include "ohci_boot.h"
#ifdef NGB_PLAYER_BUILD
#include "recomp_settings.h"
#endif
#include <stdbool.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <strings.h>
#include <string.h>
#include <time.h>
#ifdef __SWITCH__
#include <switch.h>
#endif
#include <libavcodec/avcodec.h>
#include <libavutil/mathematics.h>
#include <libswscale/swscale.h>

static const char *selected;
static bool guest_prologue;
static void seq_close(void);
static unsigned selection_edge;
static atomic_bool owns_input;
int ngb_movie_owns_input(void) { return atomic_load(&owns_input); }

/* Only known retail assets; never pass a guest path to the host filesystem. */
static const char *const titles[] = {
    "2_VI_WIDE_B.sfd","4_VI_STD_B.sfd","ninja_gaiden.sfd","doa4.sfd",
    "pre_movie1.sfd","pre_movie2.sfd","pre_movie3.sfd","pre_movie4.sfd",
    "pre_movie5.sfd","pre_movie5_j.sfd","pre_movie6.sfd","pre_movie8.sfd",
    "pre_movie8_j.sfd","pre_movie9.sfd","pre_movie10.sfd","pre_movie10_j.sfd",
    "pre_movie11.sfd","pre_movie11_j.sfd","pre_movie12.sfd","pre_movie13.sfd",
    "pre_movie13_j.sfd","pre_movie14.sfd",
};
static uint64_t selected_ns;
static atomic_bool playing;
static atomic_uint displayed;

void ngb_movie_displayed(void)
{
    if (atomic_load(&playing)) atomic_fetch_add(&displayed, 1);
}

void ngb_select_movie(uint32_t address)
{
    seq_close();
    selected = NULL;
    guest_prologue=false;
    atomic_store(&owns_input,false);
    if (!address) return;
    char path[256];
    for (unsigned i=0; i<sizeof(path); ++i) {
        char c = *(const char *)ngb_guest_pointer(address+i,1);
        path[i] = c == '\\' ? '/' : c;
        if (!c) {
            const char *name = strrchr(path, '/');
            name = name ? name+1 : path;
            for (unsigned j=0;j<sizeof titles/sizeof titles[0];++j) {
                if (strcasecmp(name,titles[j])) continue;
                selected=titles[j];
                guest_prologue=!strcmp(selected,"ninja_gaiden.sfd");
                selected_ns=ngb_elapsed_ns();
                selection_edge=ngb_movie_skip_edges();
                atomic_store(&owns_input,true);
                break;
            }
            return;
        }
    }
}

/* This Sofdec file uses one MPEG-1 pack per 2048-byte sector and puts
 * private CRI metadata before the video. Only pass video PES payloads to
 * the elementary-stream decoder. The file and input buffer stay bounded. */
/* Return one payload, 0 at the program end code, or -1 on damaged input. */
static int next_packet(FILE *file, uint8_t sector[2048+AV_INPUT_BUFFER_PADDING_SIZE], uint8_t **payload)
{
    while (fread(sector,1,2048,file)==2048) {
        if (!memcmp(sector,"\0\0\1\xb9",4)) return 0;
        if (memcmp(sector,"\0\0\1\xba",4) || memcmp(sector+12,"\0\0\1",3)) break;
        if (sector[15]!=0xe0) continue;
        size_t end=18u + ((unsigned)sector[16]<<8) + sector[17], pos=18;
        if (end>2048) break;
        while (pos<end && sector[pos]==255) ++pos;
        if (pos<end && (sector[pos]&0xc0)==0x40) pos+=2;
        if (pos>=end) break;
        unsigned flags=sector[pos];
        if (flags==15) ++pos;
        else if ((flags>>4)==2) pos+=5;
        else if ((flags>>4)==3) pos+=10;
        else break;
        if (pos>=end) break;
        memset(sector+end,0,AV_INPUT_BUFFER_PADDING_SIZE);
        *payload=sector+pos;
        return (int)(end-pos);
    }
    return -1;
}

#include "prologue_stream.inc"

static void wait_frame(uint64_t deadline)
{
    uint64_t now;
    while ((now=ngb_elapsed_ns())<deadline && !ngb_stop_requested()) {
        uint64_t ns=deadline-now;
        if (ns>8000000) ns=8000000;
#ifdef __SWITCH__
        svcSleepThread((int64_t)ns);
#else
        struct timespec delay={0,(long)ns};
        nanosleep(&delay,NULL);
#endif
    }
}

typedef struct {
    AVCodecContext *codec;
    AVFrame *frame;
    struct SwsContext *colors;
    unsigned count, late, start_edge;
    bool skipped;
    uint64_t start, period;
} Movie;

static int present_frames(Movie *movie, AVPacket *packet)
{
    int result=avcodec_send_packet(movie->codec,packet);
    if (result<0) return result;
    while ((result=avcodec_receive_frame(movie->codec,movie->frame))==0) {
        AVFrame *frame=movie->frame;
        if (frame->width!=(int)NGB_SCAN_W || frame->height!=(int)NGB_SCAN_H ||
            frame->format!=AV_PIX_FMT_YUV420P) return AVERROR_INVALIDDATA;
        if (!movie->colors) {
            AVRational rate=movie->codec->framerate;
            if (rate.num<=0 || rate.den<=0 || av_q2d(rate)<29 || av_q2d(rate)>31)
                return AVERROR_INVALIDDATA;
            movie->period=av_rescale(1000000000,rate.den,rate.num);
            movie->colors=sws_getContext(frame->width,frame->height,frame->format,
                frame->width,frame->height,AV_PIX_FMT_BGRA,SWS_POINT,NULL,NULL,NULL);
            if (!movie->colors) return AVERROR(ENOMEM);
            movie->start=ngb_elapsed_ns();
            atomic_store(&playing,true);
        }
        if (ngb_stop_requested()) return AVERROR_EXIT;
        if (movie->start_edge!=ngb_movie_skip_edges()) { movie->skipped=true; return AVERROR_EXIT; }
        uint64_t deadline=movie->start+movie->count*movie->period;
        /* Decode reference pictures, but don't present a burst of expired frames
         * after an SD stall. Keep the original movie timeline. */
        if (movie->count && ngb_elapsed_ns()>deadline+movie->period) {
            ++movie->late; ++movie->count; continue;
        }
        uint8_t *dest[4]={(uint8_t *)ngb_scanout_movie_buffer()};
        int strides[4]={4*NGB_SCAN_W};
        const uint8_t *src[4]={frame->data[0],frame->data[1],frame->data[2],NULL};
        if (sws_scale(movie->colors,src,frame->linesize,
                      0,frame->height,dest,strides)!=frame->height) return AVERROR_INVALIDDATA;
        wait_frame(deadline);
        if (ngb_stop_requested()) return AVERROR_EXIT;
        if(movie->start_edge!=ngb_movie_skip_edges()){movie->skipped=true;return AVERROR_EXIT;}
        if (ngb_elapsed_ns()>deadline+movie->period) ++movie->late;
        ngb_scanout_publish_movie();
        ++movie->count;
        if (movie->count==1) {
            uint64_t now=ngb_elapsed_ns(), press=ngb_warning_start_time();
            char log[128];
            snprintf(log,sizeof(log),"Opening movie startup start_to_frame_ms=%lld select_to_frame_ms=%llu",
                press && now>=press ? (long long)((now-press)/1000000) : -1LL,
                (unsigned long long)((now-selected_ns)/1000000));
            ngb_kernel_log(log);
        }
        if (movie->count==1 || movie->count==120) {
            char log[112];
            snprintf(log,sizeof(log),"Opening movie frame=%u elapsed_ms=%llu displayed=%u late=%u",
                movie->count,(unsigned long long)((ngb_elapsed_ns()-movie->start)/1000000),
                atomic_load(&displayed),movie->late);
            ngb_kernel_log(log);
        }
    }
    return result==AVERROR(EAGAIN) || result==AVERROR_EOF ? 0 : result;
}

static bool decode_intro(FILE *file, Movie *movie)
{
    const AVCodec *codec=avcodec_find_decoder(AV_CODEC_ID_MPEG1VIDEO);
    if (!codec) return false;
    movie->codec=avcodec_alloc_context3(codec);
    movie->frame=av_frame_alloc();
    AVCodecParserContext *parser=av_parser_init(AV_CODEC_ID_MPEG1VIDEO);
    AVPacket *packet=av_packet_alloc();
    bool complete=false;
    if (movie->codec && movie->frame && parser && packet) {
        /* A single ARM decoder owns the stream. The UI and input workers
         * keep their own cores even in hbmenu applet mode. */
        movie->codec->thread_count=1;
        int error=avcodec_open2(movie->codec,codec,NULL);
        uint8_t sector[2048+AV_INPUT_BUFFER_PADDING_SIZE];
        uint8_t *data=NULL;
        int size=0;
        while (!error && !ngb_stop_requested()) {
            if (!size) size=next_packet(file,sector,&data);
            if (size<0) break;
            int consumed=av_parser_parse2(parser,movie->codec,&packet->data,&packet->size,
                    size ? data : NULL,size,AV_NOPTS_VALUE,AV_NOPTS_VALUE,0);
            if (consumed<0 || (size && !consumed && !packet->size)) break;
            if (packet->size) error=present_frames(movie,packet);
            if (!size) {
                complete=!error && present_frames(movie,NULL)==0 && movie->count>0;
                break;
            }
            data+=consumed;
            size-=consumed;
        }
    }
    if (parser) av_parser_close(parser);
    av_packet_free(&packet);
    return complete;
}

uint32_t ngb_movie_status(uint32_t status)
{
    /* PREP and PLAYING both identify an initialized game movie session.
     * Native playback can start at PREP without priming the Xbox decoder. */
    /* The New Game narration and subtitles are timed and composited by the
     * title between polls. A blocking native playback here starves that loop. */
    if (guest_prologue) {
        if (seq.file) {
            if (selection_edge==ngb_movie_skip_edges() && seq_playing()) return 2;
            seq_close(); status=3;
        } else if (status==1 || status==2) {
            if (selection_edge==ngb_movie_skip_edges()) return status;
            status=3;
        } else if (status==0) return status;
        guest_prologue=false;
        selected=NULL;
        atomic_store(&owns_input,false);
        return status;
    }
    if (!selected || (status!=1 && status!=2)) return status;
    const char *name=selected;
    selected=NULL;
#ifndef __SWITCH__
    if (getenv("NGB_TEST_ORIGINAL_MOVIE")) { atomic_store(&owns_input,false); return status; }
#endif
#ifdef NGB_PLAYER_BUILD
    if (ngb_settings_skip_intro() && (!strcmp(name,"2_VI_WIDE_B.sfd") || !strcmp(name,"4_VI_STD_B.sfd"))) {
        atomic_store(&owns_input,false);
        return 3;
    }
#endif
    FILE *file=ngb_open_disc_movie(name);
    if (!file) { atomic_store(&owns_input,false); return status; }
    if (status==1) ngb_kernel_log("Opening movie native playback during guest prep");
    setvbuf(file,NULL,_IOFBF,128*1024);
    Movie movie={.start=ngb_elapsed_ns(),.start_edge=selection_edge};
    atomic_store(&displayed,0);
    bool complete=decode_intro(file,&movie);
    if (complete) wait_frame(movie.start+movie.count*movie.period);
    atomic_store(&playing,false);
    atomic_store(&owns_input,false);
    sws_freeContext(movie.colors);
    av_frame_free(&movie.frame);
    avcodec_free_context(&movie.codec);
    fclose(file);
    char log[144];
    snprintf(log,sizeof(log),"Opening movie %s frames=%u elapsed_ms=%llu displayed=%u late=%u",
        ngb_stop_requested() ? "cancelled" : movie.skipped ? "skipped" : complete ? "EOF" : "fallback",movie.count,
        (unsigned long long)((ngb_elapsed_ns()-movie.start)/1000000),atomic_load(&displayed),movie.late);
    ngb_kernel_log(log);
    return (complete || movie.skipped) && !ngb_stop_requested() ? 3 : status; /* MWPLY_STAT_PLAYEND */
}
