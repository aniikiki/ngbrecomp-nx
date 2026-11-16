"""Measure actual main-thread journal application in isolation, with exact
inputs, separating raw per-byte, runtime packing and already-packed output.
The prepared case never drops a masked write; surrounding bytes may change."""
from pathlib import Path
import subprocess as sp
here=Path(__file__).resolve().parent;d=Path('/work/build/switch-runtime/opt050/actor-journal')
s=(d/'standalone.c').read_text()
a=' memcpy(j->ram,j->init,RAM);'
b=''' unsigned *ends=calloc(events+2,4),*rawends=calloc(events+2,4);struct patch *patches=malloc(n*sizeof(*patches));struct packer*pack=calloc(1,sizeof *pack);unsigned count=0,c=0,blocks=0;
 for(unsigned k=1;k<=events;k++){if(((j->ticks-events+k)&63)&&k!=events)continue;
  while(c<n&&(k==events||writes[c][0]<k)){if(!store_byte(pack,writes[c][1],writes[c][2]))abort();c++;}
  memcpy(patches+count,pack->out,pack->used*sizeof(*patches));count+=pack->used;ends[blocks]=count;rawends[blocks++]=c;
  for(unsigned i=0;i<pack->used;i++)pack->entry[pack->touched[i]]=0;pack->used=0;}
 memcpy(j->ram,j->init,RAM);
 for(unsigned r=0;r<39;r++){unsigned mode=r%3;struct timespec t0,t1;
 clock_gettime(CLOCK_MONOTONIC,&t0);
 for(unsigned rep=0;rep<8;rep++){unsigned lo=0;unsigned fake=0;
 for(unsigned k=0;k<blocks;k++){
  if(!mode){for(;lo<rawends[k];lo++)j->ram[writes[lo][1]]=writes[lo][2];}
  else if(mode==1){for(;lo<rawends[k];lo++)if(!store_byte(pack,writes[lo][1],writes[lo][2]))abort();apply(pack,j->ram);}
  else {for(;lo<ends[k];lo++){struct patch v=patches[lo];uint8_t *dst=j->ram+v.address;
   if(v.mask==15)memcpy(dst,&v.value,4);else for(unsigned a=0;a<4;a++)if(v.mask&(1u<<a))dst[a]=v.value>>(8*a);}}
  __asm__ volatile("":::"memory");}}
 clock_gettime(CLOCK_MONOTONIC,&t1);
 if(r>=3)printf("[APPLY_COST] id=%u mode=%u ns=%llu\\n",j->meta[2],mode,(unsigned long long)(((t1.tv_sec-t0.tv_sec)*1000000000ll+t1.tv_nsec-t0.tv_nsec)/8));}
 free(pack);free(patches);free(ends);free(rawends);
'''+a
s='#include "packed-trace.c"\n'+s.replace(a,b)
(d/'compact-bench.c').write_text(s);sp.run(['cc','-D_GNU_SOURCE','-O2','-I'+str(here),d/'compact-bench.c',d/'actor.o',d.parent.parent/'core-perf/thread-pointer.o','-l:libz.so.1','-pthread','-lm','-o',d/'compact-bench'],check=True)
