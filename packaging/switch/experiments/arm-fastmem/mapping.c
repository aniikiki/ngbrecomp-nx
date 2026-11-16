// Private to the Linux test runner. The original RAM and the guest view share
// the same physical backing. Uncommitted/special pages are inaccessible here.
#define _GNU_SOURCE
#include <sys/mman.h>
#include <ucontext.h>
#include <signal.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#define PAGE 4096u
#define LOW (64u << 20)
#define VIEW ((size_t)1 << 32)
unsigned char *ngb_alias;
extern uint16_t ngb_fast_page_bytes[];
extern const int32_t __start_ngb_fault[], __stop_ngb_fault[];
struct fix { uintptr_t pc, slow; };
static struct fix *sites;
static size_t nsite;
static volatile sig_atomic_t faults;
static struct sigaction previous;
static int cmp(const void *a, const void *b) {
    uintptr_t x=((const struct fix*)a)->pc, y=((const struct fix*)b)->pc;
    return (x>y)-(x<y);
}
static void trap(int sig, siginfo_t *info, void *ctx) {
    ucontext_t *u=ctx;
    if ((uintptr_t)info->si_addr - (uintptr_t)ngb_alias < VIEW + PAGE) {
        uintptr_t pc=u->uc_mcontext.pc;
        size_t lo=0,hi=nsite;
        while(lo<hi) {
            size_t m=lo+(hi-lo)/2;
            if (sites[m].pc < pc) lo=m+1; else hi=m;
        }
        if (lo<nsite && sites[lo].pc==pc) {
            ++faults; u->uc_mcontext.pc=sites[lo].slow; return;
        }
    }
    // This is an isolated diagnostic process. Never continue an unknown fault.
    _exit(128+sig);
}
void *ngb_alias_create(void) {
    if (sysconf(_SC_PAGESIZE)!=PAGE) abort();
    int fd=memfd_create("ngb-offline-ram",MFD_CLOEXEC);
    if (fd<0 || ftruncate(fd,2*LOW)) abort();
    unsigned char *ram=mmap(NULL,2*LOW,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
    ngb_alias=mmap(NULL,VIEW+PAGE,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE,-1,0);
    if(ram==MAP_FAILED || ngb_alias==MAP_FAILED) abort();
    if (mmap(ngb_alias,LOW,PROT_NONE,MAP_FIXED|MAP_SHARED,fd,0)!=ngb_alias ||
        mmap(ngb_alias+0x80000000u,2*LOW,PROT_NONE,MAP_FIXED|MAP_SHARED,fd,0)!=ngb_alias+0x80000000u) abort();
    close(fd);
    nsite=(__stop_ngb_fault-__start_ngb_fault)/2;
    sites=calloc(nsite,sizeof(*sites)); if(!sites||!nsite) abort();
    for(size_t i=0;i<nsite;i++){
        const int32_t *r=__start_ngb_fault+2*i;
        sites[i]=(struct fix){(uintptr_t)r+r[0],(uintptr_t)(r+1)+r[1]};
    }
    qsort(sites,nsite,sizeof(*sites),cmp);
    struct sigaction sa={0};sa.sa_sigaction=trap;sa.sa_flags=SA_SIGINFO;sigemptyset(&sa.sa_mask);
    if(sigaction(SIGSEGV,&sa,&previous))abort();
    return ram;
}
void ngb_alias_sync(unsigned first,unsigned count) {
    if(!ngb_alias)return;
    for(unsigned end=first+count;first<end;) {
        unsigned last=first+1;int rw=ngb_fast_page_bytes[first]!=0;
        while(last<end && (ngb_fast_page_bytes[last]!=0)==rw)++last;
        if(mprotect(ngb_alias+(size_t)first*PAGE,(last-first)*PAGE,rw?PROT_READ|PROT_WRITE:PROT_NONE))abort();
        first=last;
    }
}
void ngb_alias_destroy(void *ram) {
    if (!ngb_alias) return;
    fprintf(stderr,"[FASTMEM] sites=%zu recovered_faults=%d\n",nsite,(int)faults);
    sigaction(SIGSEGV,&previous,NULL);munmap(ngb_alias,VIEW+PAGE);munmap(ram,2*LOW);
    free(sites);ngb_alias=NULL;
}
