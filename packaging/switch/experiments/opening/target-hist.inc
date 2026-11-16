struct th_row {unsigned table,va;unsigned long long hits;};
static struct th_row th_rows[4096];
static _Thread_local unsigned th_on;
void th_observe(unsigned table,unsigned va){
 if(!th_on)return;
 unsigned ix=((table*2654435761u)^(va*16777619u))>>20;
 for(unsigned n=0;n<4096;++n,ix=(ix+1)&4095){
  struct th_row *r=&th_rows[ix];
  if(!r->hits){r->table=table;r->va=va;}
  if(r->table==table && r->va==va){++r->hits;return;}
 }
 abort();
}
void phase_flip(unsigned f){
 th_on=0;
 if(f==30||f==120)for(unsigned i=0;i<4096;i++)if(th_rows[i].hits)
  fprintf(stderr,"[TARGET_HIST] %u %x %x %llu\n",f,th_rows[i].table,th_rows[i].va,th_rows[i].hits);
 if(f==0||f==30)memset(th_rows,0,sizeof th_rows);
 th_on=f<120;
}
