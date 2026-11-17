// Emit a deterministic device-boundary trace for comparison to the 0.56.17 mixer.
#define main check_main
#include "check.c"
#undef main
int main(void){
 ngb_audio_reset();
 apu_config[NV_PAPU_VPVADDR/4]=0x1000;apu_config[NV_PAPU_VPSGEADDR/4]=0x5800;
 uint32_t pages[]={0x7000,0,0x9000,0};memcpy(ram+0x5800,pages,sizeof pages);
 for(unsigned i=0;i<4096;i++){ram[0x7000+i]=i*19+3;ram[0x9000+i]=i*13+9;}
 int16_t out[4096];
 for(unsigned j=0;j<4096;j++){
  unsigned id=64;uint32_t *v=voice_record(id);
  unsigned e=j/32,ch=1+(e%2),type=(unsigned[]){0,1,3,2}[e/2%4];
  unsigned bits=(unsigned[]){0,1,2,3}[type==3?2+e/8%2:type];
  unsigned fmt=(type<<30)|(bits<<28)|((ch-1)<<27)|((ch-1+(e%3==2))<<16)|NV_PAVS_VOICE_CFG_FMT_LOOP;
  if(e%7==2)fmt &= ~NV_PAVS_VOICE_CFG_FMT_LOOP;
  v[NV_PAVS_VOICE_CFG_FMT/4]=fmt;
  v[NV_PAVS_VOICE_CFG_VBIN/4]=(j%13==2)?1:32;
  v[NV_PAVS_VOICE_TAR_VOLA/4]=(j%16<4)?0x1230123:0xf000f;
  v[NV_PAVS_VOICE_TAR_VOLB/4]=v[NV_PAVS_VOICE_TAR_VOLC/4]=~0u;
  if(j%11==0)ngb_apu_write(0xfe820204,(j/11)%8);
  v[NV_PAVS_VOICE_CUR_PSL_START/4]=4091+e%8;
  v[NV_PAVS_VOICE_PAR_NEXT/4]=43+e%17;v[NV_PAVS_VOICE_CUR_PSH_SAMPLE/4]=11;
  int pitch=(int[]){0,1,-3919,3211,4096,21103,-32768,32767}[(j/3)%8];
  v[NV_PAVS_VOICE_TAR_PITCH_LINK/4]=(uint32_t)(uint16_t)pitch<<16;
  if(j%32==0){v[NV_PAVS_VOICE_PAR_OFFSET/4]=3;fractional_samples[id]=0.51;}
  if(j%8!=0){
    active_voices[1]=1;v[NV_PAVS_VOICE_PAR_STATE/4]=NV_PAVS_VOICE_PAR_STATE_ACTIVE_VOICE;
  }else active_voices[1]=0;
  now+=(j%29==0)?64000000:666667;
  advance_buffer_voices();
  unsigned n=atomic_load(&queues[0].write)-atomic_load(&queues[0].read);
  assert(n<=2048);ngb_pcm_render(out,n);

   fwrite(&n,sizeof n,1,stdout);fwrite(out,4,n,stdout);
   fwrite(v+NV_PAVS_VOICE_PAR_OFFSET/4,4,1,stdout);fwrite(fractional_samples+id,8,1,stdout);
   fwrite(v+NV_PAVS_VOICE_PAR_STATE/4,4,1,stdout);

 }
}
