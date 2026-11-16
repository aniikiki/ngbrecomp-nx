"""Round-trip *every byte at every poll* against raw write events. Mutate
untouched neighboring bytes between epochs to test masked publication."""
from pathlib import Path
import subprocess as sp
here=Path(__file__).resolve().parent;d=Path('/work/build/switch-runtime/opt050/actor-journal')
s=(d/'standalone.c').read_text()
a=' for(unsigned k=0;k<n;k++){if(writes[k][1]>=RAM||writes[k][0]>events)abort();j->ram[writes[k][1]]=writes[k][2];}'
b=''' struct packer *pack=calloc(1,sizeof(*pack));unsigned char*ref=malloc(RAM);if(!pack||!ref)abort();memcpy(ref,j->init,RAM);
 unsigned cursor=0,packed=0,intervals=0;for(unsigned t=0;t<=events;t++){
  if((t!=events && ((j->ticks-events+t)&63))||!t)continue;
  unsigned start=cursor;while(cursor<n&&(t==events||writes[cursor][0]<t)){unsigned *e=writes[cursor++];if(e[1]>=RAM||e[0]>events)abort();if(!store_byte(pack,e[1],e[2]))abort();ref[e[1]]=e[2];}
  for(unsigned k=0;k<pack->used;k++){struct patch *v=pack->out+k;for(unsigned z=0;z<4;z++)if(!(v->mask&(1u<<z))){
    uint8_t value=ref[v->address+z]^0x97;j->ram[v->address+z]=ref[v->address+z]=value;
  }}
  packed+=pack->used;intervals++;apply(pack,j->ram);
  for(unsigned i=start;i<cursor;i++)if(memcmp(ref+(writes[i][1]&~3u),j->ram+(writes[i][1]&~3u),4))abort();
 }
 if(cursor!=n||memcmp(ref,j->ram,RAM))abort();printf("[PACKED_JOURNAL] id=%u raw=%u masked_words=%u boundaries=%u identical=1\\n",j->meta[2],n,packed,intervals);
 memcpy(j->ram,j->init,RAM);for(unsigned k=0;k<n;k++)j->ram[writes[k][1]]=writes[k][2];free(ref);free(pack);'''
assert a in s;s='#include "packed-trace.c"\n'+s.replace(a,b)
(d/'packed.c').write_text(s)
sp.run(['cc','-D_GNU_SOURCE','-O2','-I'+str(here),d/'packed.c',d/'actor.o',d.parent.parent/'core-perf/thread-pointer.o','-l:libz.so.1','-pthread','-lm','-o',d/'packed'],check=True)
