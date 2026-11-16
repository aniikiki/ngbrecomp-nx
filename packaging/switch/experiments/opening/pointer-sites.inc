extern char __executable_start[];
struct pointer_site {uintptr_t pc;unsigned calls;unsigned sizes[5];unsigned long long bytes;};
static _Thread_local struct pointer_site ps_rows[8192];
static _Thread_local unsigned ps_on, ps_lost;
uintptr_t pointer_site_resolve(uint32_t va,size_t bytes,uintptr_t lr){
 if(ps_on){
 uintptr_t pc=lr-4-(uintptr_t)__executable_start;
 unsigned i=((pc>>2)*2654435761u)>>19 & 8191, n=0;
 for(;n<8192;n++,i=(i+1)&8191){
 struct pointer_site *r=ps_rows+i;
 if(r->calls && r->pc!=pc)continue;
 r->pc=pc;r->calls++;r->bytes+=bytes;r->sizes[bytes==0?0:bytes<=4?1:bytes<=16?2:bytes<=64?3:4]++;break;
 }
 ps_lost+=n==8192;
 }
 return ngb_guest_pointer(va,bytes);
}
void phase_flip(unsigned f){
 if(f==30||f==120){
 fprintf(stderr,"[POINTER_SITES] %u lost=%u\n",f,ps_lost);
 for(unsigned i=0;i<8192;i++){struct pointer_site *r=ps_rows+i;if(r->calls)
 fprintf(stderr,"[PS] %u %lx %u %llu %u %u %u %u %u\n",f,(unsigned long)r->pc,r->calls,r->bytes,r->sizes[0],r->sizes[1],r->sizes[2],r->sizes[3],r->sizes[4]);}
 }
 if(!f||f==30){memset(ps_rows,0,sizeof ps_rows);ps_lost=0;}
 ps_on=f<120;
}
