#include "audio_output.h"
#include <stdatomic.h>
// Movie PES packets can lead the picture; guest audio is wall-clock paced.
enum { GAME_CAP=4096, MOVIE_CAP=65536 };
static int16_t game_pcm[GAME_CAP][2],movie_pcm[MOVIE_CAP][2];
typedef struct {int16_t (*pcm)[2];unsigned cap,seen_discard;atomic_uint read,write,discard;} PcmQueue;
static PcmQueue queues[2]={{.pcm=game_pcm,.cap=GAME_CAP},{.pcm=movie_pcm,.cap=MOVIE_CAP}};
NgbMoviePcmPosition ngb_pcm_movie_position(void)
{
    return (NgbMoviePcmPosition){
        .read = atomic_load_explicit(&queues[1].read, memory_order_acquire),
        .written = atomic_load_explicit(&queues[1].write, memory_order_relaxed)
    };
}
void ngb_pcm_submit(unsigned movie,const int16_t *s,unsigned n){
    PcmQueue *q=&queues[movie];unsigned w=atomic_load_explicit(&q->write,memory_order_relaxed);
    unsigned space=q->cap-(w-atomic_load_explicit(&q->read,memory_order_acquire));if(n>space)n=space;
    unsigned pos=w&(q->cap-1),first=q->cap-pos;if(first>n)first=n;
    if(s){memcpy(q->pcm[pos],s,4*first);memcpy(q->pcm,s+2*first,4*(n-first));}
    else{memset(q->pcm[pos],0,4*first);memset(q->pcm,0,4*(n-first));}
    atomic_store_explicit(&q->write,w+n,memory_order_release);
}
void ngb_pcm_flush(unsigned movie){
    PcmQueue *q=&queues[movie];atomic_store(&q->discard,atomic_load(&q->write));
}
static int16_t pcm_clip(int x){return x>32767?32767:x< -32768?-32768:x;}
void ngb_pcm_render(int16_t *dst,unsigned n){
    memset(dst,0,n*4);
    for(unsigned i=0;i<2;i++){
        PcmQueue *q=&queues[i];unsigned r=atomic_load(&q->read),cut=atomic_load(&q->discard);
        if(cut!=q->seen_discard){if(cut-r<=q->cap)r=cut;q->seen_discard=cut;}
        unsigned avail=atomic_load_explicit(&q->write,memory_order_acquire)-r;if(avail>n)avail=n;
        for(unsigned j=0;j<avail;j++){
            int16_t *p=q->pcm[(r+j)&(q->cap-1)];
            for(unsigned c=0;c<2;c++)dst[2*j+c]=pcm_clip(dst[2*j+c]+p[c]);
        }
        atomic_store_explicit(&q->read,r+avail,memory_order_release);
    }
}
#ifdef __SWITCH__
#include <switch.h>
#include <sys/stat.h>
static _Alignas(4096) int16_t speakers[3][2048];
static AudioOutBuffer device_buffers[3];
static Thread device_worker;
static atomic_bool device_running;
static void output_error(Result rc){
    mkdir("sdmc:/switch/ngb-runtime/logs",0777);
    FILE *f=fopen("sdmc:/switch/ngb-runtime/logs/error.log","a");
    if(f){fprintf(f,"[AUDIO] audout error %08x\n",rc);fclose(f);}
}
static void play_pcm(void *arg){
    (void)arg;
    while(atomic_load(&device_running)){
        AudioOutBuffer *buf=NULL;u32 count=0;
        Result rc=audoutWaitPlayFinish(&buf,&count,50000000);
        if(rc==KERNELRESULT(TimedOut))continue;
        if(R_FAILED(rc)){output_error(rc);break;}
        while(buf && count--){
            AudioOutBuffer *next=buf->next;buf->next=NULL;
            ngb_pcm_render(buf->buffer,512);armDCacheFlush(buf->buffer,2048);
            rc=audoutAppendAudioOutBuffer(buf);
            if(R_FAILED(rc)){output_error(rc);return;}buf=next;
        }
    }
}
int ngb_audio_device_open(void){
    Result rc=audoutInitialize();if(R_FAILED(rc)){output_error(rc);return 0;}
    rc=audoutStartAudioOut();
    if(R_SUCCEEDED(rc))for(unsigned i=0;i<3;i++){
        device_buffers[i]=(AudioOutBuffer){.buffer=speakers[i],.buffer_size=4096,.data_size=2048};
        armDCacheFlush(speakers[i],2048);
        rc=audoutAppendAudioOutBuffer(device_buffers+i);if(R_FAILED(rc))break;
    }
    if(R_SUCCEEDED(rc))rc=threadCreate(&device_worker,play_pcm,NULL,NULL,32768,0x2a,-2);
    if(R_SUCCEEDED(rc)){
        atomic_store(&device_running,true);rc=threadStart(&device_worker);
        if(R_SUCCEEDED(rc))return 1;
        atomic_store(&device_running,false);threadClose(&device_worker);
    }
    output_error(rc);audoutStopAudioOut();audoutExit();return 0;
}
void ngb_audio_device_close(void){
    if(!atomic_exchange(&device_running,false))return;
    threadWaitForExit(&device_worker);threadClose(&device_worker);audoutStopAudioOut();audoutExit();
}
#endif
