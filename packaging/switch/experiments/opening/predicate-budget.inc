unsigned pred_on,pred_n,pred_inside,pred_rand;
static unsigned clockmode;static unsigned nchild,nsamp,pframe,zerochild,invalid,repeat,repeatok,retok,childcase[64];
static uint64_t tparent,tchild,sumparent,sumchild,baseline;
static uint64_t stamp(void){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
struct pk{unsigned obj,row,arg,actor;};
struct pv{struct pk k;unsigned f,seen,result;unsigned char state[29];};
static struct pv slots[16384],*active;
static int same;
static unsigned char *ordinary(unsigned char *r,unsigned a,unsigned n){
 unsigned off=a&0x7fffffffu;if(off>=0x08000000||n>0x08000000-off)return 0;
 for(unsigned i=a>>12;i<=(a+n-1)>>12;i++)if(ngb_fast_page_bytes[i]!=4096)return 0;
 return r+off;
}
void pred_parent_in(unsigned char *ram0,unsigned obj,unsigned row,unsigned sp,unsigned actor){
 if(pred_inside)abort();
 pred_inside=1;++nsamp;
 if(pred_on==2){
 ++pred_n;active=0;same=0;
 unsigned char *v=ordinary(ram0,row,10),*arg=ordinary(ram0,sp+4,4),*o=ordinary(ram0,obj+0x2774,0x7d);
 unsigned char *a=ordinary(ram0,actor+0x2774,10);if(!v||!arg||!o){static unsigned shown;if(shown++<4)fprintf(stderr,"[PRED_INVALID] obj=%08x row=%08x sp=%08x actor=%08x\n",obj,row,sp,actor);++invalid;return;}
 struct pk key={obj,row,0,actor};memcpy(&key.arg,arg,4);
 unsigned char state[29];memcpy(state,v,10);memcpy(state+10,o,2);memcpy(state+12,o+8,4);state[16]=o[0x7c];state[17]=ram0[0x589755];memcpy(state+18,o+0x25,5);memcpy(state+23,ram0+0x4968b0+state[16]*0xdd0+0x1e0,2);
 if(a){memcpy(state+25,a,2);memcpy(state+27,a+8,2);}else memset(state+25,0,4);
 unsigned at=((obj*2654435761u)^(row*40503u)^(key.arg*49157u));at=(at^(at>>16))&16383;
 for(unsigned n=0;n<16384;n++,at=(at+1)&16383){struct pv *p=slots+at;
  if(p->f!=pframe){p->f=pframe;p->k=key;p->seen=0;}
  if(memcmp(&key,&p->k,sizeof key))continue;
  active=p;if(p->seen){++repeat;same=!memcmp(p->state,state,29);repeatok+=same;}
  memcpy(p->state,state,29);return;
 }abort();
 }
 if(clockmode!=2)tparent=stamp();
}
void pred_child_in(unsigned char *r,unsigned obj,unsigned kind,unsigned sp,unsigned ax){
 (void)obj;(void)ax;if(pred_on==2){unsigned char *args=ordinary(r,sp+4,4);if(!args)abort();memcpy(&kind,args,4);kind &=255;}
 ++nchild;if(pred_on==2){++childcase[kind<63?kind:63];return;}if(clockmode==2)tchild=stamp();
}
void pred_child_out(unsigned ax){if(pred_on==1){if(clockmode==2)sumchild+=stamp()-tchild;}else zerochild+=ax==0;}
void pred_parent_out(unsigned ax){
 if(pred_on==1){if(clockmode!=2)sumparent+=stamp()-tparent;}
 else if(active){retok+=same && ax==active->result;active->result=ax;active->seen=1;}
 pred_inside=0;
}
void pred_flip(unsigned f){
 if(pred_inside)abort();
 if(f)fprintf(stderr,"[PRED] %u %u %u %u %llu %llu %u %u %u %u %u\n",f,pred_n,nsamp,nchild,(unsigned long long)sumparent,(unsigned long long)sumchild,invalid,repeat,repeatok,retok,zerochild);
 if(f==120){for(unsigned i=0;i<64;i++)if(childcase[i])fprintf(stderr,"[PRED_KIND] %u %u\n",i,childcase[i]);}
 if(!f){clockmode=getenv("NGB_PRED_CHILD")?2:1;uint64_t a=stamp();for(unsigned i=0;i<10000;i++)baseline=stamp();fprintf(stderr,"[CLOCK_READ] %llu\n",(unsigned long long)((baseline-a)/10000));}
 pred_n=nsamp=nchild=invalid=repeat=repeatok=retok=zerochild=0;sumparent=sumchild=0;
 pframe=f+1;pred_rand=(f+1)*2246822519u;pred_on=f>=120?0:getenv("NGB_PRED_INPUT")?2:1;
}
