typedef unsigned long long bl_u;
static _Thread_local struct bl_bucket{bl_u calls,n[2],ns[2];} bl[512];
static _Thread_local unsigned bl_gen,bl_rng,bl_active;
static bl_u bl_tick(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return (bl_u)t.tv_sec*1000000000+t.tv_nsec;}
bl_u bl_start(int fn){
 if(!bl_active)return 0;
 if((unsigned)fn>=512)abort();
 struct bl_bucket *b=&bl[fn];b->calls++;
 bl_rng=bl_rng*1664525u+1013904223u;
 switch(bl_rng>>27){
 case 0:return (bl_tick()<<2)|bl_gen;
 case 1:{bl_u t=bl_tick();b->ns[1]+=bl_tick()-t;b->n[1]++;}
 }
 return 0;
}
void bl_end(int fn,bl_u t){if(t&&bl_active&&(t&3)==bl_gen){bl[fn].ns[0]+=bl_tick()-(t>>2);bl[fn].n[0]++;}}
static void bl_boundary(unsigned f){
 if(f!=0&&f!=30&&f!=120)return;
 if(f)for(unsigned i=0;i<512;i++)if(bl[i].calls)fprintf(stderr,"[BEFORE_COST] %u %u %llu %llu %llu %llu %llu\n",f,i,bl[i].calls,bl[i].n[0],bl[i].ns[0],bl[i].n[1],bl[i].ns[1]);
 memset(bl,0,sizeof bl);bl_active=f!=120;bl_gen=f==0?1:2;bl_rng=35819+f;
}
