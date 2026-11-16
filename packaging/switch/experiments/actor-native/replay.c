/* Standalone Linux ARM tester for the unchanged devkitA64 worker object.
 * Feed it game-owner captures locally; no Xbox assets should be distributed. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include "gz-abi.h"
#include <time.h>
enum {RAM=128u<<20};
extern unsigned ngb_actor_native(void*,unsigned char*,const uint16_t*,uint64_t*,uint64_t*);
struct job {uint32_t meta[6];uint8_t regs[512],expect[512],*ram,*init,*bytes,*seen;uint16_t *pages;uint32_t *at;uint64_t ticks,entries,ns;unsigned error;};
static int readn(gzFile f,void*p,unsigned n){return gzread(f,p,n)==(int)n;}
static int load(struct job*j,const char*path){
 gzFile f=gzopen(path,"rb");uint64_t time[2];
 if(!f||!readn(f,j->meta,24)||j->meta[0]!=0x4e474241||j->meta[3]>512||j->meta[4]>131072||!readn(f,time,16))return 0;
 j->ticks=time[0];unsigned n=j->meta[4],r=j->meta[3];
 j->ram=malloc(RAM);j->init=malloc(RAM);j->seen=calloc(RAM,1);j->pages=malloc(2u<<20);j->at=malloc(n*4);j->bytes=malloc(n);
 if(!j->ram||!j->init||!j->seen||!j->pages||!j->at||!j->bytes)return 0;
 if(!readn(f,j->regs,r)||!readn(f,j->expect,r)||!readn(f,j->pages,2u<<20)||!readn(f,j->ram,RAM))return 0;
 memcpy(j->init,j->ram,RAM);
 for(unsigned i=0;i<n;i++){if(!readn(f,&j->at[i],4)||j->at[i]>=RAM||!readn(f,j->bytes+i,1)||j->seen[j->at[i]])return 0;j->seen[j->at[i]]=1;}
 return gzgetc(f)<0 && gzclose(f)==Z_OK;
}
static void *run(void*arg){struct job*j=arg;struct timespec a,b;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&a);
 j->error=ngb_actor_native(j->regs,j->ram,j->pages,&j->ticks,&j->entries);
 clock_gettime(CLOCK_THREAD_CPUTIME_ID,&b);j->ns=(b.tv_sec-a.tv_sec)*1000000000ll+b.tv_nsec-a.tv_nsec;return 0;}
int main(int argc,char**argv){if(argc<2||argc>3)return 2;struct job j[2]={0};pthread_t threads[2];int ok=1;
 for(int i=0;i<argc-1;i++)if(!load(j+i,argv[i+1]))return 3;
 for(int i=0;i<argc-1;i++)if(pthread_create(threads+i,0,run,j+i))abort();
 for(int i=0;i<argc-1;i++)if(pthread_join(threads[i],0))abort();
 for(int i=0;i<argc-1;i++){struct job*v=j+i;unsigned diff=0,regs=0,extra=0;
 for(unsigned k=0;k<v->meta[4];k++){uint32_t a=v->at[k];if(v->ram[a]!=v->bytes[k]){if(diff<8)printf("mem %08x got=%02x want=%02x\n",a,v->ram[a],v->bytes[k]);++diff;}}
 for(unsigned k=0;k<v->meta[3];k++)if(v->regs[k]!=v->expect[k]){if(regs<5)printf("reg %u got=%02x want=%02x\n",k,v->regs[k],v->expect[k]);regs++;}
 for(unsigned p=0;p<RAM;p+=4096)if(memcmp(v->init+p,v->ram+p,4096))for(unsigned k=p;k<p+4096;k++)extra+=!v->seen[k]&&v->init[k]!=v->ram[k];
 printf("[ACTOR_JOB] frame=%u id=%u error=%08x writes=%u diff=%u extra=%u regs=%u thread_ns=%llu\n",v->meta[1],v->meta[2],v->error,v->meta[4],diff,extra,regs,(unsigned long long)v->ns);
 ok &= !(v->error||diff||regs||extra);}
 return !ok;
}
