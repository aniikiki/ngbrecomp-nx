/* Logical reuse distances of table cache lines, not measured hardware misses.
   Only these five units and dynamic MEM32 participate; other traffic omitted. */
extern uint32_t opening_end4[];
static _Thread_local struct {unsigned phase,used;uintptr_t mru[16];uint64_t hist[2][17];} tl;
void ws_observe(unsigned u,unsigned site,unsigned va){
 (void)u;(void)site;if(!tl.phase)return;
 uintptr_t line=(uintptr_t)&opening_end4[va>>12]>>6;
 unsigned j=0;while(j<tl.used && tl.mru[j]!=line)++j;
 ++tl.hist[tl.phase-1][j<tl.used?j:16];
 if(j==16)j=15;else if(j==tl.used)++tl.used;
 for(;j>0;--j)tl.mru[j]=tl.mru[j-1];
 tl.mru[0]=line;
}
void phase_flip(unsigned f){
 if(f==0){tl.phase=1;tl.used=0;}
 if(f==30)tl.phase=2;
 if(f==120){tl.phase=0;
 for(unsigned k=0;k<2;k++){fprintf(stderr,"[TABLE_LOCALITY] %u",k);
 for(unsigned j=0;j<17;j++)fprintf(stderr," %llu",(unsigned long long)tl.hist[k][j]);
 fputc('\n',stderr);}}
}
