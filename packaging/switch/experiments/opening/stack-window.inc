extern uint32_t opening_end4[];
static _Thread_local unsigned sw_on;
static unsigned long long sw_pages[129][4];
static unsigned sw_full[128];
static unsigned sw_contig_min,sw_contig_max,sw_flips;
static void sw_snapshot(void){
 unsigned n=0;
 while(n<128 && opening_end4[0x1180+n]==((0x1180u+n)<<12)+4093u)n++;
 if(n<sw_contig_min)sw_contig_min=n;
 if(n>sw_contig_max)sw_contig_max=n;
 for(unsigned i=0;i<128;i++)sw_full[i]+=(opening_end4[0x1180+i]==((0x1180u+i)<<12)+4093u);
 ++sw_flips;
}
void sw_observe(unsigned va,unsigned op){
 if(!sw_on)return;
 unsigned pg=(va>>12)-0x1180u;
 ++sw_pages[pg<128?pg:128][op+2*(va>=opening_end4[va>>12])];
}
void phase_flip(unsigned f){
 if(f)sw_snapshot();
 if(f==30||f==120){
 fprintf(stderr,"[SW_MAP] %u %u %u %u\n",f,sw_flips,sw_contig_min,sw_contig_max);
 for(unsigned i=0;i<128;i++)fprintf(stderr,"[SW_FULL] %u %u %u\n",f,i,sw_full[i]);
 for(unsigned i=0;i<129;i++){unsigned long long *r=sw_pages[i];if(r[0]||r[1]||r[2]||r[3])
 fprintf(stderr,"[SW_PAGE] %u %u %llu %llu %llu %llu\n",f,i,r[0],r[1],r[2],r[3]);}
 }
 if(!f||f==30){memset(sw_pages,0,sizeof sw_pages);memset(sw_full,0,sizeof sw_full);sw_flips=sw_contig_max=0;sw_contig_min=128;}
 sw_on=f<120;
}
