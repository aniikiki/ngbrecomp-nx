// Offline regression at the device boundary. No sound device, saves or SD card needed.
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "audio_boot.c"
#include <libavcodec/avcodec.h>
#include "movie_audio.inc"
static uint8_t ram[65536];static uint64_t now;
void *ngb_dma_pointer(uint32_t a,size_t n){assert(a+n<=sizeof ram);return ram+a;}
void ngb_kernel_log(const char *s){fprintf(stderr,"%s\n",s);}
void ngb_stop(const char *s,uint32_t x){fprintf(stderr,"%s %x\n",s,x);abort();}
uint64_t ngb_elapsed_ns(void){return now;}
static void voices(void){
    int16_t out[128],l=8192,r=-1234;
    ngb_audio_reset();unsigned id=64;
    apu_config[NV_PAPU_VPVADDR/4]=0x1000;apu_config[NV_PAPU_VPSGEADDR/4]=0x5800;
    uint32_t pages[]={0x7000,0,0x9000,0};memcpy(ram+0x5800,pages,sizeof pages);
    uint32_t *v=voice_record(id);
    v[NV_PAVS_VOICE_CFG_FMT/4]=(1u<<30)|(1<<28)|(1<<27)|(1<<16)|NV_PAVS_VOICE_CFG_FMT_LOOP;
    v[NV_PAVS_VOICE_CFG_VBIN/4]=32;
    v[NV_PAVS_VOICE_TAR_VOLA/4]=0xf000f;v[NV_PAVS_VOICE_TAR_VOLB/4]=v[NV_PAVS_VOICE_TAR_VOLC/4]=~0u;
    v[NV_PAVS_VOICE_CUR_PSL_START/4]=4094;v[NV_PAVS_VOICE_PAR_NEXT/4]=1;
    memcpy(ram+0x7ffe,&l,2);memcpy(ram+0x9000,&r,2);
    apu_config[NV_PAPU_FEAV/4]=1<<16;start_voice(id);now=666667;ngb_audio_poll();ngb_pcm_render(out,32);
    for(unsigned i=0;i<32;i++)assert(out[i*2]==(i%2?0:l) && out[i*2+1]==(i%2?0:r));
    v[NV_PAVS_VOICE_PAR_STATE/4]|=NV_PAVS_VOICE_PAR_STATE_PAUSED;now+=666667;ngb_audio_poll();ngb_pcm_render(out,32);
    for(unsigned i=0;i<64;i++)assert(!out[i]);
    // One 64-sample mono Xbox ADPCM block, played twice as fast and looped.
    v[NV_PAVS_VOICE_PAR_STATE/4]&=~NV_PAVS_VOICE_PAR_STATE_PAUSED;
    v[NV_PAVS_VOICE_CFG_FMT/4]=(2u<<30)|(2u<<28)|NV_PAVS_VOICE_CFG_FMT_LOOP;
    v[NV_PAVS_VOICE_CUR_PSL_START/4]=4096;v[NV_PAVS_VOICE_PAR_NEXT/4]=63;
    v[NV_PAVS_VOICE_TAR_PITCH_LINK/4]=4096u<<16;
    memset(ram+0x9000,0,36);ram[0x9001]=16;
    now+=666667;ngb_audio_poll();ngb_pcm_render(out,32);
    assert(!(v[NV_PAVS_VOICE_PAR_OFFSET/4]&NV_PAVS_VOICE_PAR_OFFSET_CBO));
    for(unsigned i=0;i<64;i++)assert(out[i]==4096);
    // Guest rewrites a block at the same virtual and physical address.
    ram[0x9001]=32;
    now+=666667;ngb_audio_poll();ngb_pcm_render(out,32);
    for(unsigned i=0;i<64;i++)assert(out[i]==8192);
    int16_t src[128];for(unsigned i=0;i<128;i++)src[i]=30000;
    ngb_pcm_submit(0,src,64);ngb_pcm_submit(1,src,64);ngb_pcm_render(out,32);assert(out[0]==32767);
    ngb_pcm_flush(1);ngb_pcm_render(out,64);assert(out[0]==30000 && out[64]==0);
    puts("PASS: SGE page split, stereo PCM, Xbox ADPCM, double pitch, loop, pause, saturation and movie skip");
}
static void movie(const char *path){
    FILE *f=fopen(path,"rb");assert(f);uint8_t s[2048];uint64_t source=0,frames=0,nonzero=0;
    unsigned rate=0;int peak=0;int16_t out[4096*2];movie_audio_end();
    while(fread(s,1,sizeof s,f)==sizeof s){
        if(memcmp(s,"\0\0\1\xba",4) || s[15]!=0xc0)continue;
        unsigned end=18+s[16]*256+s[17],p=18;assert(end<=2048);
        while(p<end && s[p]==255)p++;
        if((s[p]&0xc0)==0x40)p+=2;
        p+=s[p]==15?1:s[p]>>4==2?5:10;assert(p<end);
        if(!rate){uint8_t *h=s+p;source=(uint32_t)h[12]<<24|h[13]<<16|h[14]<<8|h[15];rate=h[8]<<24|h[9]<<16|h[10]<<8|h[11];}
        movie_audio_packet(s+p,end-p);
        unsigned n=atomic_load(&queues[1].write)-atomic_load(&queues[1].read);assert(n<4096);
        ngb_pcm_render(out,n);frames+=n;
        for(unsigned i=0;i<2*n;i++){int a=abs(out[i]);if(a>peak)peak=a;nonzero+=a!=0;}
    }
    fclose(f);assert(rate && frames==(source*48000+rate-1)/rate && peak>256 && nonzero>frames/10);
    printf("PASS %s: %u Hz -> 48000 Hz, %llu frames, peak %d\n",path,rate,(unsigned long long)frames,peak);
}
int main(int argc,char **argv){voices();for(int i=1;i<argc;i++)movie(argv[i]);}
