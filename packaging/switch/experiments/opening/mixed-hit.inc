unsigned mh_on;
static struct {unsigned va,hits,checks;} mh[2048];
void mh_hit(unsigned va,unsigned n){
 unsigned idx=(va*2654435761u)>>21;
 while(mh[idx].va&&mh[idx].va!=va)idx=(idx+1)&2047;
 mh[idx].va=va;mh[idx].hits++;mh[idx].checks+=n-1;
}
void phase_flip(unsigned f){
 if(f==30||f==120){unsigned h=0,c=0;for(unsigned i=0;i<2048;i++)if(mh[i].va){h+=mh[i].hits;c+=mh[i].checks;fprintf(stderr,"[MIXED_OWNER] %u %x %u %u\n",f,mh[i].va,mh[i].hits,mh[i].checks);}fprintf(stderr,"[MIXED_HIT] %u %u %u\n",f,h,c);}
 if(!f||f==30){memset(mh,0,sizeof mh);}mh_on=f<120;
}
