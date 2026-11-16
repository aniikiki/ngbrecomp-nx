"""Sample device-pending probes separately; exclude guest interrupt handlers.
Never change the order, multiplicity or return value of the device calls."""
def instrument(rt):
    key='static void poll_callbacks(void)\n{'
    assert rt.count(key)==1
    pos=rt.index(key)
    head=rt[:pos]
    body,tail=rt[pos:].split('#include "workers.inc"',1)
    pre=r'''
static unsigned irq_frame,irq_rng[4];
static unsigned long long irq_tot[4][7];
static uint64_t irq_clock(void){
 struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();
 return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;
}
void irq_window(unsigned f){
 if(f==30||f==120)for(unsigned j=0;j<4;j++){
 unsigned long long *v=irq_tot[j];
 fprintf(stderr,"[IRQ_COST] %u %u %llu %llu %llu %llu %llu %llu %llu\n",f,j,v[0],v[1],v[2],v[3],v[4],v[5],v[6]);}
 if(!f||f==30)memset(irq_tot,0,sizeof irq_tot);
 if(!f){for(unsigned j=0;j<4;j++)irq_rng[j]=1231+j*867;}
 irq_frame=f<120?f+1:0;
}
#define IRQ_MEASURE(id,expr) ({unsigned f=irq_frame;uint32_t result; \
 if(!f){result=(expr);}else{unsigned long long *v=irq_tot[id];++v[0]; \
 unsigned pick=(irq_rng[id]=irq_rng[id]*1664525u+1013904223u)>>27; \
 if(pick){result=(expr);}else{uint64_t a=irq_clock(),b=irq_clock();result=(expr);uint64_t c=irq_clock(); \
 if(f==irq_frame){++v[1];v[2]+=c-b;v[3]+=b-a;if(result){++v[4];v[5]+=c-b;}}} \
 if(f==irq_frame && result)++v[6];}result;})
'''
    for i,k in enumerate(('ngb_ohci_irq_pending()','ngb_audio_irq(5)','ngb_audio_irq(6)','ngb_nv2a_irq_pending()')):
        assert body.count(k)==1
        body=body.replace(k,'IRQ_MEASURE('+str(i)+','+k+')')
    return head+pre+body+'#include "workers.inc"'+tail
