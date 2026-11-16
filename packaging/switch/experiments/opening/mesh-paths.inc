unsigned mp_epoch=121;
static struct {unsigned n,c[2];unsigned char p[192];} paths[256];
static unsigned mp_used,mp_over[2],mp_cross;
void mp_finish(unsigned e,const unsigned char*p,unsigned n){
 if(e!=mp_epoch){mp_cross++;return;}unsigned w=e>=30;
 if(n>192){mp_over[w]++;return;}
 unsigned i=0;for(;i<mp_used;i++)if(paths[i].n==n && !memcmp(p,paths[i].p,n))break;
 if(i==mp_used){if(i==256){mp_over[w]++;return;}paths[i].n=n;memcpy(paths[i].p,p,n);mp_used++;}
 paths[i].c[w]++;
}
void phase_flip(unsigned f){
 mp_epoch=f;
 if(f==120){fprintf(stderr,"[MP_TOTAL] %u %u %u %u\n",mp_used,mp_over[0],mp_over[1],mp_cross);
 for(unsigned i=0;i<mp_used;i++){fprintf(stderr,"[MP_PATH] %u %u ",paths[i].c[0],paths[i].c[1]);for(unsigned j=0;j<paths[i].n;j++)fprintf(stderr,"%02x",paths[i].p[j]);fputc('\n',stderr);}}
}
