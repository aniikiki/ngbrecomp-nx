unsigned at_on;
static struct {unsigned root,key,mask;} at_nodes[8192];
static unsigned at_calls[2],at_unique[2],at_common,at_full;
void at_visit(unsigned i,unsigned root,unsigned key){
 unsigned j=((root>>4)*2654435761u+key*2246822519u)&8191;
 for(unsigned n=0;n<8192;n++,j=(j+1)&8191){
  if(!at_nodes[j].mask){at_nodes[j].root=root;at_nodes[j].key=key;}
  if(at_nodes[j].root!=root||at_nodes[j].key!=key)continue;
  at_calls[i]++;unsigned bit=1u<<i;
  if(!(at_nodes[j].mask&bit)){at_unique[i]++;if(at_nodes[j].mask)at_common++;at_nodes[j].mask|=bit;}
  return;
 }
 at_full++;
}
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[ACTOR_TREE] %u visits=%u/%u unique=%u/%u shared=%u overflow=%u\n",f,at_calls[0],at_calls[1],at_unique[0],at_unique[1],at_common,at_full);
 if(!f||f==30){memset(at_calls,0,sizeof at_calls);memset(at_unique,0,sizeof at_unique);at_full=at_common=0;}
 memset(at_nodes,0,sizeof at_nodes);at_on=f<120;
}
