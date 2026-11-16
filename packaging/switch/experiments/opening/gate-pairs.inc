extern char __executable_start[];
unsigned gp_on;
struct gp_row {uintptr_t lr,target; uint64_t calls,pad;};
_Static_assert(sizeof(struct gp_row)==32,"asm stride");
struct gp_row gp_rows[8192];
void phase_flip(unsigned f){
 if(f==30||f==120){
 unsigned long long total=0;
 for(unsigned i=0;i<8192;i++)if(gp_rows[i].calls){
 total+=gp_rows[i].calls;
 fprintf(stderr,"[GP] %u %lx %lx %llu\n",f,(unsigned long)(gp_rows[i].lr-4-(uintptr_t)__executable_start),(unsigned long)(gp_rows[i].target-(uintptr_t)__executable_start),(unsigned long long)gp_rows[i].calls);
 }
 fprintf(stderr,"[GP_TOTAL] %u %llu\n",f,total);
 }
 if(!f||f==30)memset(gp_rows,0,sizeof gp_rows);
 gp_on=f<120;
}
