"""Same prepared tiles, replay all 64 starting phases with synthetic phase
changes between callbacks. Compare to the raw timestamped stores at each
publication boundary, not just the final array."""
from pathlib import Path
import subprocess as sp
here=Path(__file__).resolve().parent;d=Path('/work/build/switch-runtime/opt050/actor-journal')
s=(d/'standalone.c').read_text();a=' memcpy(j->ram,j->init,RAM);';b=r'''
 unsigned nb=0,np=0,c=0;unsigned et[1025],end[1025],pe[1025];struct patch *pp=malloc(sizeof(*pp)*n);struct packer*pk=calloc(1,sizeof *pk);
 for(unsigned t=1;t<=events;t++){if(t%8 && t!=events)continue;
  while(c<n&&(t==events||writes[c][0]<t)){if(!store_byte(pk,writes[c][1],writes[c][2]))abort();c++;}
  memcpy(pp+np,pk->out,pk->used*sizeof(*pp));np+=pk->used;pe[nb]=np;end[nb]=c;et[nb++]=t;
  for(unsigned q=0;q<pk->used;q++)pk->entry[pk->touched[q]]=0;pk->used=0;}
 uint8_t *ref=malloc(RAM);if(!ref)abort();unsigned exits=0,full=0,edge=0;
 memcpy(ref,j->init,RAM);memcpy(j->ram,j->init,RAM);
 for(unsigned phase=0;phase<64;phase++){unsigned cur=0,b=0,r=0,t=1+phase;
  for(;;){if(t>events)t=events;unsigned before=r;
   while(r<n&&(t==events||writes[r][0]<t)){ref[writes[r][1]]=writes[r][2];r++;}
   while(b<nb&&et[b]<=t){unsigned start=b?end[b-1]:0;
    if(cur==start){full++;for(unsigned q=b?pe[b-1]:0;q<pe[b];q++){struct patch v=pp[q];for(unsigned z=0;z<4;z++)if(v.mask&(1<<z))j->ram[v.address+z]=v.value>>(z*8);}}
    else while(cur<end[b]){j->ram[writes[cur][1]]=writes[cur][2];cur++;edge++;}
    cur=end[b++];}
   while(cur<n&&(t==events||writes[cur][0]<t)){j->ram[writes[cur][1]]=writes[cur][2];cur++;edge++;}
   if(cur!=r)abort();for(unsigned q=before;q<r;q++){unsigned addr=writes[q][1]&~3u;if(memcmp(j->ram+addr,ref+addr,4))abort();}
   if(t==events)break;
   // A resumed fiber may advance the global ticket an arbitrary amount.
   if(r>before){unsigned a=writes[before][1]^1;j->ram[a]^=0xa5;ref[a]^=0xa5;}
   exits++;t+=1+((t*17+phase*37)%64);
  }}
 if(memcmp(j->ram,ref,RAM))abort();free(ref);free(pk);free(pp);
 printf("[TILE_OK] id=%u phases=64 checks=%u tiles=%u edge_bytes=%u\n",j->meta[2],exits,full,edge);
'''+a
s='#include "packed-trace.c"\n'+s.replace(a,b)
(d/'tile-check.c').write_text(s);sp.run(['cc','-D_GNU_SOURCE','-O2','-I'+str(here),d/'tile-check.c',d/'actor.o',d.parent.parent/'core-perf/thread-pointer.o','-pthread','-l:libz.so.1','-lm','-o',d/'tile-check'],check=True)
