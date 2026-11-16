/* Linux experiment: canonical RAM stays accessible to the emulator; a separate
 * 4 GiB guest-indexed view makes unhandled guest pages inaccessible to the CPU. */
extern uint32_t opening_end4[];
unsigned char *guard_active;
static unsigned char *guard_area;
#define G_LENGTH ((size_t)1<<32)
static void guard_setup(int fd){
 guard_area=mmap(NULL,G_LENGTH,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE,-1,0);
 if(guard_area==MAP_FAILED)abort();
 for(unsigned i=0;i<2;i++){unsigned char *at=guard_area+i*bias;
 if(mmap(at,span,PROT_NONE,MAP_SHARED|MAP_FIXED,fd,0)!=at)abort();}
}
static void guard_protect(unsigned pg,unsigned pages,int grant){
 size_t addr=(size_t)pg<<12;
 if(grant&&((addr&0x7fffffffU)+(size_t)pages*4096>span))abort();
 if(mprotect(guard_area+addr,(size_t)pages*4096,grant?(PROT_READ|PROT_WRITE):PROT_NONE))abort();
}
void guard_update(unsigned pg){if(guard_active)guard_protect(pg,1,opening_end4[pg]!=0);}
void guard_flip(unsigned f){
 if(f==0){if(!guard_area||guard_active||sysconf(_SC_PAGESIZE)!=4096)abort();
 if(mprotect(guard_area,G_LENGTH,PROT_NONE))abort();
 for(unsigned pg=0;pg<(1u<<20);){if(!opening_end4[pg]){pg++;continue;}
 unsigned begin=pg++;while(pg<(1u<<20)&&opening_end4[pg])pg++;guard_protect(begin,pg-begin,1);}
 guard_active=guard_area;fprintf(stderr,"[GUARD_VIEW] armed\n");}
 if(f==120){guard_active=NULL;fprintf(stderr,"[GUARD_VIEW] completed\n");}
}
