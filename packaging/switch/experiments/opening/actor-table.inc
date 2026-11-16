unsigned at_on;
static struct {unsigned root,index,mask;} at_tab[512];
static unsigned at_calls[2],at_seen[2],at_repeated[2],at_pair,at_over;
void at_observe(unsigned side,unsigned root,unsigned idx){
 unsigned j=0;at_calls[side]++;
 while(j<512 && at_tab[j].mask && (at_tab[j].root!=root || at_tab[j].index!=idx))++j;
 if(j==512){at_over++;return;}
 at_tab[j].root=root;at_tab[j].index=idx;
 unsigned mask=at_tab[j].mask,bit=1u<<side;
 if(mask&bit)at_repeated[side]++;else{at_seen[side]++;if(mask)at_pair++;}
 at_tab[j].mask=mask|bit;
}
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[ACTOR_TABLE] %u %u %u %u %u %u %u %u %u\n",f,at_calls[0],at_calls[1],at_seen[0],at_seen[1],at_repeated[0],at_repeated[1],at_pair,at_over);
 if(!f||f==30){memset(at_calls,0,sizeof at_calls);memset(at_seen,0,sizeof at_seen);memset(at_repeated,0,sizeof at_repeated);at_pair=at_over=0;}
 memset(at_tab,0,sizeof at_tab);at_on=f<120;
}
