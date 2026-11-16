/* A trained world may never silently use a stale byte on a missing page.
   Check both a missing stack slot and an unsupported actor through the actual
   cross-compiled object with synthetic (locally owned) register inputs. */
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
extern unsigned ngb_actor_sparse(void*,uint8_t*,const uint16_t*,uint64_t*,uint64_t*,uint16_t*,uint8_t*,uint16_t*,unsigned*,uint8_t*);
int main(void){
 uint32_t r[128]={0},prior[128];uint8_t *ram=calloc(1,128<<20),*slots=calloc(512,4096),*foot=calloc(32768,1);uint16_t *pages=calloc(1,2<<20),*index=calloc(32768,2),touched[512];unsigned used=0;uint64_t p=0,e=0;
 if(!ram||!slots||!foot||!pages||!index)return 2;
 r[3]=0x1140200;r[6]=0x4b4e50;memcpy(prior,r,sizeof r);
 unsigned err=ngb_actor_sparse(r,ram,pages,&p,&e,index,slots,touched,&used,foot);
 if(err!=r[3]+20||used||p||e||memcmp(prior,r,sizeof r))return 3;
 unsigned pg=r[3]>>12;pages[pg]=4096;
 err=ngb_actor_sparse(r,ram,pages,&p,&e,index,slots,touched,&used,foot);
 if(!err||used!=1||touched[0]!=pg||memcmp(prior,r,sizeof r)||p||e)return 4;
 for(unsigned j=0;j<128u<<20;j++)if(ram[j])return 5;
 printf("missing stack byte and missing game data aborted; shared 128 MiB and registers unchanged\n");
}
