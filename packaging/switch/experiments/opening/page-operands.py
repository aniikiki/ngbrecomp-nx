"""For this sampler, classify only the exact scaled LDR Wt,[x27,Xm,LSL #2]."""
def instrument(s):
    k='static volatile sig_atomic_t pc_used'
    s=s.replace(k,'static unsigned page_rows[8192][2];\n'+k)
    k='if(pc_used<8192){';assert s.count(k)==1
    s=s.replace(k,k+'''
 uintptr_t ip=((ucontext_t*)ctx)->uc_mcontext.pc;
 // ARM Linux replay only; its executable PT_LOAD is readable (runner checks).
 if(ip>=page_text_lo && ip+4<=page_text_hi){
 uint32_t op=*(const uint32_t*)ip;
 if((op & ~0x001f001fu)==0xb8607b60u){
 unsigned rm=(op>>16)&31;
 uint64_t page=rm==31?0:((ucontext_t*)ctx)->uc_mcontext.regs[rm];
 if(page<0x100000){page_rows[pc_used][0]=1;page_rows[pc_used][1]=(unsigned)page;}
 }}
''')
    k='for(int j=0;j<pc_used;j++)fprintf(stderr,"[FRAME_PC]'
    s=s.replace(k,'for(int j=0;j<pc_used;j++)if(page_rows[j][0])fprintf(stderr,"[PAGE_PC] %u %lx %x\\n",pc_rows[j].frame,(unsigned long)pc_rows[j].pc,page_rows[j][1]);\n '+k)
    # Use dl_iterate_phdr outside signal handling, only the main binary's executable readable segment.
    k='static unsigned page_rows'
    s=s.replace(k,'''#include <link.h>
static uintptr_t page_text_lo,page_text_hi;
static int page_segment(struct dl_phdr_info* d,size_t n,void *arg){
 (void)n;(void)arg;
 if(d->dlpi_name && *d->dlpi_name)return 0;
 for(unsigned i=0;i<d->dlpi_phnum;i++){
 const ElfW(Phdr)*h=&d->dlpi_phdr[i];
 if(h->p_type==PT_LOAD && (h->p_flags&(PF_X|PF_R))==(PF_X|PF_R)){
 page_text_lo=d->dlpi_addr+h->p_vaddr;page_text_hi=page_text_lo+h->p_memsz;break;}}
 return 1;}
'''+k)
    return s.replace('if(!f){','if(!f){dl_iterate_phdr(page_segment,NULL);if(!page_text_hi)abort();',1)
