unsigned av_on;
static unsigned av_rng=281, av_seq[2],av_cnt[2],av_blank[2],av_pairs,av_diff[5],av_dup,av_full;
static unsigned long long av_ns[2],av_empty[2];
static unsigned av_tab[512][8];
static unsigned long long av_clock(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return t.tv_sec*1000000000ull+t.tv_nsec;}
unsigned long long av_begin(unsigned side){
 if(!av_on)return 0;
 av_rng=1664525u*av_rng+1013904223u;unsigned sample=av_rng>>27;
 if(sample==0)return av_clock();
 if(sample==1){unsigned long long t=av_clock();av_empty[side]+=av_clock()-t;av_blank[side]++;}
 return 0;
}
void av_end(unsigned side,unsigned long long t,unsigned root,unsigned idx,unsigned sel,unsigned actor,unsigned ptr,unsigned base,unsigned result){
 if(t){av_ns[side]+=av_clock()-t;av_cnt[side]++;}av_seq[side]++;
 unsigned j=0,v[5]={sel,actor,ptr,base,result};
 while(j<512&&av_tab[j][0]&&(av_tab[j][1]!=root||av_tab[j][2]!=idx))++j;
 if(j==512){av_full++;return;}
 unsigned *r=av_tab[j];unsigned bit=1u<<side;
 if(r[0]&bit){av_dup++;return;}
 if(r[0]){av_pairs++;for(unsigned k=0;k<5;k++)av_diff[k]+=(r[3+k]!=v[k]);}
 else{r[1]=root;r[2]=idx;memcpy(r+3,v,sizeof v);}
 r[0]|=bit;
}
void phase_flip(unsigned f){
 if(f==30||f==120){
 fprintf(stderr,"[ACTOR_VALUES] %u %u %u %u %u %u %u %u %u\n",f,av_pairs,av_dup,av_full,av_diff[0],av_diff[1],av_diff[2],av_diff[3],av_diff[4]);
 for(unsigned i=0;i<2;i++)fprintf(stderr,"[ACTOR_PREFIX] %u %u %u %u %llu %u %llu\n",f,i,av_seq[i],av_cnt[i],av_ns[i],av_blank[i],av_empty[i]);
 }
 if(!f||f==30){av_pairs=av_dup=av_full=0;memset(av_diff,0,sizeof av_diff);memset(av_seq,0,sizeof av_seq);memset(av_cnt,0,sizeof av_cnt);memset(av_ns,0,sizeof av_ns);memset(av_blank,0,sizeof av_blank);memset(av_empty,0,sizeof av_empty);}
 memset(av_tab,0,sizeof av_tab);av_on=f<120;
}
