#define _GNU_SOURCE
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
extern void *__real_calloc(size_t,size_t);
extern void __real_free(void*);
static unsigned char *area;
enum { span=128u<<20 };
#define bias ((size_t)1<<31)
void *__wrap_calloc(size_t n,size_t bytes){
 if(n!=1||bytes!=span)return __real_calloc(n,bytes);
 if(area)abort();
 int fd=memfd_create("ngb-replay-ram",MFD_CLOEXEC);
 if(fd<0||ftruncate(fd,span))abort();
 area=mmap(NULL,bias+span,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE,-1,0);
 if(area==MAP_FAILED)abort();
 for(unsigned i=0;i<2;i++){
  unsigned char *at=area+bias*i;
  if(mmap(at,span,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,fd,0)!=at)abort();
 }
 close(fd);
 volatile unsigned char *v=area;
 v[span-1]=91;if(v[bias+span-1]!=91)abort();v[bias+span-1]=0;if(v[span-1])abort();
 fprintf(stderr,"[ALIAS_RAM] shared views verified\n");
 return area;
}
void __wrap_free(void *p){
 if(area && p==area){if(munmap(area,bias+span))abort();area=NULL;return;}
 __real_free(p);
}
