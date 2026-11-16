unsigned tt_on;
static struct {unsigned root,key,ptr,kind,mask,changed;} tt[2048];
static unsigned tc[3],td,tf,tall,tsame;
void tt_visit(unsigned i,unsigned r,unsigned k,unsigned p,unsigned v){
 tc[i]++;unsigned j=((r>>4)*2654435761u+k*2246822519u)&2047;
 for(unsigned n=0;n<2048;n++,j=(j+1)&2047){
  if(!tt[j].mask){tt[j].root=r;tt[j].key=k;tt[j].ptr=p;tt[j].kind=v;}
  if(tt[j].root!=r||tt[j].key!=k)continue;
  if(tt[j].mask&(1u<<i))td++;
  tt[j].changed|=tt[j].ptr!=p||tt[j].kind!=v;
  tt[j].mask|=1u<<i;return;
 }
 tf++;
}
void phase_flip(unsigned f){
 if(tt_on)for(unsigned j=0;j<2048;j++)if(tt[j].mask==7){tall++;tsame+=!tt[j].changed;}
 if(f==30||f==120)fprintf(stderr,"[TREE_TRIPLE] %u calls=%u/%u/%u all=%u same=%u dup=%u overflow=%u\n",f,tc[0],tc[1],tc[2],tall,tsame,td,tf);
 if(!f||f==30){memset(tc,0,sizeof tc);td=tf=tall=tsame=0;}
 memset(tt,0,sizeof tt);tt_on=f<120;
}
