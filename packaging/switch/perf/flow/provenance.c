#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
enum {RAM=128u<<20, S=6};
static _Thread_local unsigned phase,role;
struct cell {
    uint32_t pc; uint8_t writer,readers,epoch;
    uint8_t previous_writer,previous_epoch,input_epoch,own_epoch,stale_epoch,output_epoch;
};
static uint8_t *render_begin;
static uint8_t render_epoch;
static unsigned incoming,stale,outputs,activations;
static uint8_t input_pages[RAM/4096],output_pages[RAM/4096];
static uint64_t past_reads[S][S];
static struct cell *slices[RAM/4096];
static struct cell *cell_at(unsigned at){
    struct cell **slot=&slices[at/4096];if(!*slot){*slot=calloc(4096,sizeof(**slot));if(!*slot)abort();}
    struct cell *c=*slot+(at&4095);
    uint8_t epoch=(uint8_t)phase;
    if(c->epoch!=epoch){c->epoch=epoch;c->writer=c->readers=0;}
    return c;
}
extern char __executable_start;
struct site {unsigned a,b,writer,reader,first,bytes;};
static struct site sites[65536];static unsigned overflow;
static void raw_site(unsigned a,unsigned b,unsigned writer,unsigned reader,unsigned at){
    unsigned h=((a>>2)*2654435761u ^ (b>>2)*2246822519u ^ (writer<<4) ^ reader)&65535;
    for(unsigned n=0;n<256;n++,h=(h+1)&65535){
        struct site *site=sites+h;
        if(!site->bytes){*site=(struct site){a,b,writer,reader,at,1};return;}
        if(site->a==a && site->b==b && site->writer==writer && site->reader==reader){site->bytes++;return;}
    }
    ++overflow;
}
static uint8_t *base;
unsigned trial_variant;
static uint64_t events[2][S],edges[3][S][S],equalwrites[S];
static uint32_t edge_page[3][S][S][RAM>>16];
static const unsigned tasks[S]={0,0x1ca790,0x1cb9a0,0x151150,0x320e0,0};
static struct {uint8_t *data;unsigned count,task,pc;uint8_t old[16];} pending;
static uint8_t *large; static size_t capacity;
static inline void dep(unsigned kind,unsigned from,unsigned to,unsigned at){
    if(!from || from==to)return;
    ++edges[kind][from][to];++edge_page[kind][from][to][at>>16];
}
static inline void finish(void){
    if(!pending.count)return;
    unsigned src=pending.task,n=pending.count,at=(uintptr_t)pending.data-(uintptr_t)base;
    pending.count=0;
    for(unsigned j=0;j<n;j++){
        if((n<=16?pending.old:large)[j]==base[at+j]){++equalwrites[src];continue;}
        struct cell *c=cell_at(at+j);
        c->previous_epoch=(uint8_t)phase;c->previous_writer=src;
        c->own_epoch=src==1?(uint8_t)phase:0;
        if(src==1 && c->output_epoch!=(uint8_t)phase){
            c->output_epoch=(uint8_t)phase;++outputs;output_pages[(at+j)>>12]=1;
        }
        dep(2,c->writer,src,at+j);
        for(unsigned k=1;k<S;k++)if(c->readers&(1u<<k))dep(1,k,src,at+j);
        c->readers=0;c->writer=src;c->pc=pending.pc;
    }
}
void dep_key(unsigned k){
    if(phase)finish();
    unsigned before=role;role=5;
    for(unsigned j=1;j<=4;j++)if(tasks[j]==k)role=j;
    if(phase && role==1){
        if(before!=1)++activations;
        if(render_epoch!=(uint8_t)phase){
            if(!render_begin){render_begin=malloc(RAM);if(!render_begin)abort();}
            memcpy(render_begin,base,RAM);render_epoch=(uint8_t)phase;
        }
    }
}
void dep_bind(void *ram){base=ram;}
void dep_flip(unsigned f,unsigned task){
    if (phase) {
        finish();
        fprintf(stderr,"[FLOW_FRAME] %u\n",phase);
        for(unsigned i=1;i<S;i++){
            fprintf(stderr,"[FLOW_WORK] %u %u %llu %llu %llu\n",phase,i,(unsigned long long)events[0][i],(unsigned long long)events[1][i],(unsigned long long)equalwrites[i]);
            for(unsigned j=1;j<S;j++)for(unsigned k=0;k<3;k++)if(edges[k][i][j]){
                unsigned hot=0;for(unsigned page=1;page<RAM>>16;page++)if(edge_page[k][i][j][page]>edge_page[k][i][j][hot])hot=page;
                fprintf(stderr,"[FLOW] %u %u %u %u %llu %08x %u\n",phase,k,i,j,(unsigned long long)edges[k][i][j],hot<<16,edge_page[k][i][j][hot]);
            }
        }
        unsigned nr=0,nw=0;
        for(unsigned j=0;j<RAM/4096;j++){nr+=input_pages[j];nw+=output_pages[j];}
        fprintf(stderr,"[RENDER_SET] %u inputs %u stale %u outputs %u pages %u %u resumes %u\n",
            phase,incoming,stale,outputs,nr,nw,activations);
        for(unsigned a=1;a<S;a++)for(unsigned b=1;b<S;b++)if(past_reads[a][b])
            fprintf(stderr,"[PAST_READ] %u %u %u %llu\n",phase,a,b,(unsigned long long)past_reads[a][b]);
        incoming=stale=outputs=activations=0;memset(input_pages,0,sizeof input_pages);
        memset(output_pages,0,sizeof output_pages);memset(past_reads,0,sizeof past_reads);
        memset(edges,0,sizeof edges);memset(edge_page,0,sizeof edge_page);memset(events,0,sizeof events);memset(equalwrites,0,sizeof equalwrites);
    }
    phase=(f>=1801 && f<=1805)?f:0;trial_variant=!!phase;
    if(phase){
        /* Legacy per-frame fields reset lazily. Older producer identity survives. */
        if(!base)abort();
    }
    if(f==1806){
        fprintf(stderr,"[FLOW_LOST_SITES] %u\n",overflow);
        for(unsigned i=0;i<65536;i++)if(sites[i].bytes){
            struct site v=sites[i];fprintf(stderr,"[FLOW_SITE] %u %u %x %x %x %u\n",v.writer,v.reader,v.a,v.b,v.first,v.bytes);
        }
    }
    dep_key(task);
}
static inline void observe(void *address,unsigned n,int write,uintptr_t pc){
    if(!phase)return;
    finish();
    uintptr_t at=(uintptr_t)address-(uintptr_t)base;
    if(!n || n>RAM || at>RAM-n)return;
    ++events[write][role];
    if(write){pending.pc=(uint32_t)(pc-(uintptr_t)&__executable_start);pending.data=address;pending.count=n;pending.task=role;if(n>16 && n>capacity){large=realloc(large,n);if(!large)abort();capacity=n;}memcpy(n<=16?pending.old:large,address,n);return;}
    for(unsigned j=0;j<n;j++){
        struct cell *c=cell_at(at+j);
        if(c->previous_writer && c->previous_epoch!=(uint8_t)phase)
            ++past_reads[c->previous_writer][role];
        if(role==1 && c->own_epoch!=(uint8_t)phase){
            if(c->input_epoch!=(uint8_t)phase){
                c->input_epoch=(uint8_t)phase;++incoming;input_pages[(at+j)>>12]=1;
            }
            if(c->stale_epoch!=(uint8_t)phase && base[at+j]!=render_begin[at+j]){
                c->stale_epoch=(uint8_t)phase;++stale;
            }
        }
        dep(0,c->writer,role,at+j);if(c->writer && c->writer!=role)raw_site(c->pc,(uint32_t)(pc-(uintptr_t)&__executable_start),c->writer,role,at+j);c->readers|=1u<<role;
    }
}
#include "tsan-hooks.inc"
