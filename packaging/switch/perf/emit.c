#include <stdio.h>
#include <stdlib.h>
struct gcov_info;
extern const struct gcov_info *__start_ngb_training[], *__stop_ngb_training[];
void __gcov_info_to_gcda(const struct gcov_info*,void(*)(const char*,void*),void(*)(const void*,unsigned,void*),void*(*)(unsigned,void*),void*);
static void fname(const char* name,void* f){*(FILE**)f=fopen(name,"wb");if(!*(FILE**)f)abort();}
static void data(const void* v,unsigned n,void* f){if(fwrite(v,1,n,*(FILE**)f)!=n)abort();}
static void* alloc(unsigned n,void*unused){(void)unused;return malloc(n);}
static void emit(void){int n=0;for(const struct gcov_info **it=__start_ngb_training;it<__stop_ngb_training;it++){
 FILE *f=NULL;__gcov_info_to_gcda(*it,fname,data,alloc,&f);if(!f||fclose(f))abort();++n;
}fprintf(stderr,"[TRAIN] wrote %d profiles\n",n);}
__attribute__((constructor)) static void install(void){atexit(emit);}
