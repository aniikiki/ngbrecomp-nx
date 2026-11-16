"""In-order commit of actor iterations with private temporaries, preserving
all observed external inputs. Compute the optimal division into contiguous
waves, limited to two or three workers, on the exact same trace."""
from pathlib import Path
h=Path(__file__).with_name('actor-transactions.c').read_text()
h=h.replace('static unsigned stable,', '''static unsigned wave_diff[128][128],workload[128],invalid[128];
static uint8_t *image[11]; // physical guest RAM is 128 MiB. Use sparse per-page preimages instead.
static uint8_t *preimages[128][RAM/4096];static unsigned initialized[128];
static uint8_t *original_page(unsigned idx,unsigned off){
 unsigned page=off>>12;return preimages[idx][page]?preimages[idx][page]+(off&4095):NULL;
}
static unsigned stable,''').replace('static uint8_t *image[11];','')
# Sparse snapshots: on each observed original store preserve the pre-store page
# in every earlier wave. Catch external writes between actors too, regardless
# of the worker: the 47 game units are instrumented for the whole window.
h=h.replace('(void)pc;if(!frame||!active||!stage)return;flush();uintptr_t a=', '(void)pc;if(!frame)return;flush();uintptr_t a=')
anchor='if(!n||n>RAM||a>RAM-n)return;'
h=h.replace(anchor,anchor+'''
 if(wr && seq)for(unsigned p=a>>12;p<=((a+n-1)>>12);p++){
  for(unsigned i=seq;i>0;i--){if(preimages[i][p])break;
   uint8_t *v=malloc(4096);if(!v)abort();memcpy(v,base+(p<<12),4096);preimages[i][p]=v;}
 }
 if(!active || !stage)return;
''')
h=h.replace('if(!wr){inputs++;stable+=snap[off]!=base[off];}', '''if(!wr){inputs++;stable+=snap[off]!=base[off];
    for(unsigned i=1;i<seq;i++){const uint8_t *v=original_page(i,off);if(v && *v!=base[off]){if(off==sp0+20 && base[off]==id){}else wave_diff[i][seq]++;}}}
''')
h=h.replace('  fprintf(stderr,"[ACTOR_TX]', '  workload[seq]=work;invalid[seq]=unstable || mismatch;\n  fprintf(stderr,"[ACTOR_TX]')
anchor='flush();if(active)abort();seq=0;'
h=h.replace(anchor,'''flush();if(active)abort();
 if(frame){
  unsigned sum=0;for(unsigned i=1;i<=seq;i++)sum+=workload[i];
  fprintf(stderr,"[WAVE_ARGS] %u count=%u work=%u",frame,seq,sum);
  for(unsigned n=2;n<=4;n++){
   unsigned dp[128]={0},pairs[128]={0};
   for(unsigned j=1;j<=seq;j++){dp[j]=dp[j-1]+workload[j];pairs[j]=pairs[j-1];
    for(unsigned len=2;len<=n&&len<=j;len++){
     unsigned begin=j-len+1,okay=1,weight=0;
     for(unsigned k=begin;k<=j;k++){if(invalid[k]||wave_diff[begin][k])okay=0;if(workload[k]>weight)weight=workload[k];}
     if(okay && dp[begin-1]+weight<dp[j]){dp[j]=dp[begin-1]+weight;pairs[j]=pairs[begin-1]+1;}
    }}
   fprintf(stderr," %u:%u:%u",n,dp[seq],pairs[seq]);}
  fputc('\\n',stderr);
  for(unsigned i=1;i<=seq;i++)for(unsigned p=0;p<RAM/4096;p++)if(preimages[i][p]){free(preimages[i][p]);preimages[i][p]=NULL;}
  memset(wave_diff,0,sizeof wave_diff);
 }
 seq=0;''')
print(h)
