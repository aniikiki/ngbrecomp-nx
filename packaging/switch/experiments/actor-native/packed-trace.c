/* Reusable packing reference. Emit only final written bytes of each 32-bit
   word before a poll. The byte mask matters: a callback may alter adjacent
   bytes. Never replace a masked store with a full-word write. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
enum{SLOTS=8192};
struct patch {uint32_t address,value;uint8_t mask;};
struct packer {uint32_t key[SLOTS];uint16_t entry[SLOTS];struct patch out[SLOTS];uint16_t touched[SLOTS];unsigned used;};
static int store_byte(struct packer*p,uint32_t a,unsigned byte){
 uint32_t w=a>>2;unsigned slot=(w*2654435761u)>>(32-13);
 while(p->entry[slot]&&p->key[slot]!=w)slot=(slot+1)&(SLOTS-1);
 unsigned i=p->entry[slot];if(!i){if(p->used==SLOTS-1)return 0;i=++p->used;p->touched[i-1]=slot;p->key[slot]=w;p->entry[slot]=i;p->out[i-1]=(struct patch){w*4,0,0};}
 struct patch *v=p->out+i-1;unsigned sh=(a&3)*8;
 v->mask|=1u<<(a&3);v->value=(v->value&~(255u<<sh))|((uint32_t)byte<<sh);return 1;
}
static void apply(struct packer*p,unsigned char*ram){
 for(unsigned k=0;k<p->used;k++){struct patch v=p->out[k];uint8_t*d=ram+v.address;
 if(v.mask==15)memcpy(d,&v.value,4);else for(unsigned j=0;j<4;j++)if(v.mask&(1u<<j))d[j]=v.value>>(8*j);
 p->entry[p->touched[k]]=0;}p->used=0;
}
