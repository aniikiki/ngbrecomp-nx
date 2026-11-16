struct FillSite {unsigned va;unsigned long long calls,words,same,back;};
static struct FillSite fill_sites[2048];
static unsigned metering;
void ngb_fill_meter(unsigned va,unsigned n,unsigned v,int backward){
 if(!metering)return;
 unsigned i=(va*2654435761u)>>21;
 while(fill_sites[i].va && fill_sites[i].va!=va)i=(i+1)&2047;
 struct FillSite *s=fill_sites+i;s->va=va;++s->calls;s->words+=n;
 if((v&255u)*0x01010101u==v)s->same+=n;
 if(backward)s->back+=n;
}
static void fill_frame(unsigned f){metering=(f>=1800 && f<1920);
 if(f==1920)for(unsigned i=0;i<2048;i++){const struct FillSite*s=fill_sites+i;if(s->va)
 fprintf(stderr,"[FILL_SITE] %08x calls=%llu words=%llu bytesame=%llu backwards=%llu\n",s->va,s->calls,s->words,s->same,s->back);}}
