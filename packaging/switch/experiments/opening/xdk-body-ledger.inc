typedef unsigned long long xb_u;
static struct {xb_u calls,n,ns,empty,ens,switched;} xb[512];
static unsigned xb_active,xb_epoch,xb_gen,xb_rng,xb_depth,xb_sample;
static int xb_fn[128];
static xb_u xb_clock0,xb_switch0;
static xb_u xb_tick(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return (xb_u)t.tv_sec*1000000000+t.tv_nsec;}
void xbl_in(int fn){
 if(running_worker||(!xb_active&&!xb_depth))return;
 if(xb_depth>=128||(unsigned)fn>=512)abort();
 xb_fn[xb_depth++]=fn;
 if(xb_depth!=1)return;
 xb_epoch=xb_gen;xb[fn].calls++;xb_rng=xb_rng*1664525u+1013904223u;xb_sample=xb_rng>>27;
 if(xb_sample==0){xb_switch0=fiber_switches;xb_clock0=xb_tick();}
 if(xb_sample==1){xb_u t=xb_tick();xb[fn].ens+=xb_tick()-t;xb[fn].empty++;}
}
void xbl_out(int fn){
 if(running_worker||!xb_depth)return;
 if(fn!=xb_fn[--xb_depth]){fprintf(stderr,"XDK scope mismatch %d %d\n",fn,xb_fn[xb_depth]);abort();}
 if(xb_depth||!xb_active||xb_epoch!=xb_gen||xb_sample)return;
 xb_u ns=xb_tick()-xb_clock0;
 if(xb_switch0!=fiber_switches){xb[fn].switched++;return;}
 xb[fn].ns+=ns;xb[fn].n++;
}
static void xbl_boundary(unsigned f){
 if(f!=0&&f!=30&&f!=120)return;
 if(f)for(int i=0;i<512;i++)if(xb[i].calls)fprintf(stderr,"[XDK_BODY] %u %d %llu %llu %llu %llu %llu %llu\n",f,i,xb[i].calls,xb[i].n,xb[i].ns,xb[i].empty,xb[i].ens,xb[i].switched);
 memset(xb,0,sizeof xb);xb_gen++;xb_active=f!=120;xb_rng=91377+f;
}
