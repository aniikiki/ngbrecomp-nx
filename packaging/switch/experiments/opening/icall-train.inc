static struct {unsigned site, va, count;} icalls[16384];
static unsigned training_icalls;
void icall_open(unsigned site,unsigned va){
 if (!training_icalls)return;
 unsigned i=((site*2654435761u)^(va*131u>>4))&16383, start=i;
 while(icalls[i].count && (icalls[i].site!=site || icalls[i].va!=va)){i=(i+1)&16383;if(i==start)abort();}
 icalls[i].site=site;icalls[i].va=va;++icalls[i].count;
}
static void icall_flip(unsigned f){
 training_icalls=f>=30 && f<120;
 if(f==120)for(unsigned i=0;i<16384;i++)if(icalls[i].count)
  fprintf(stderr,"[ICALL_OPEN] %x %x %u\n",icalls[i].site,icalls[i].va,icalls[i].count);
}
