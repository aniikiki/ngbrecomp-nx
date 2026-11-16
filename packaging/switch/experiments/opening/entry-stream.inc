unsigned stream_on;
static struct {unsigned a,b,n;} se[32768];
static unsigned prev_va,sc,drop,starts;
void stream_visit(unsigned va){
 sc++;
 if(!prev_va){starts++;prev_va=va;return;}
 unsigned a=prev_va;prev_va=va;
 unsigned j=((a*2654435761u)^(va*2246822519u))>>17;
 for(unsigned i=0;i<128;i++,j=(j+1)&32767){
  if(!se[j].n){se[j].a=a;se[j].b=va;}
  if(se[j].a==a&&se[j].b==va){se[j].n++;return;}
 }
 drop++;
}
void phase_flip(unsigned f){
 if(f==30||f==120){unsigned total=0,edges=0;
 for(unsigned i=0;i<32768;i++)if(se[i].n){total+=se[i].n;edges++;fprintf(stderr,"[STREAM_EDGE] %u %x %x %u\n",f,se[i].a,se[i].b,se[i].n);}
 fprintf(stderr,"[STREAM_TOTAL] %u visits=%u edges=%u transitions=%u starts=%u dropped=%u\n",f,sc,edges,total,starts,drop);
 if(total+starts+drop!=sc)abort();}
 if(!f||f==30){sc=drop=starts=0;memset(se,0,sizeof se);}
 prev_va=0;stream_on=f<120;
}
