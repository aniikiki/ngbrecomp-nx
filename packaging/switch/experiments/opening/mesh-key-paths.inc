unsigned mp_epoch=121;
static struct {unsigned n;unsigned char path[192];} dict[256];
static struct {unsigned used,key,hist[256],best,total;} keys[4096];
static unsigned freq[256],global_best,global_hit,key_only,global_only;
static unsigned distinct,trained,over,cross,late,known,hit,mono,mono_hit;
void mp_finish(unsigned e,unsigned key,const unsigned char*p,unsigned n){
 if(e!=mp_epoch){cross++;return;} if(e>=30)late++;
 if(n>192){over++;return;}
 unsigned id=0;for(;id<distinct;id++)if(dict[id].n==n&&!memcmp(dict[id].path,p,n))break;
 if(id==distinct && e<30){if(id==256){over++;return;}dict[id].n=n;memcpy(dict[id].path,p,n);distinct++;}
 unsigned k=(key*2654435761u)>>20,start=k;
 while(keys[k].used&&keys[k].key!=key){k=(k+1)&4095;if(k==start){over++;return;}}
 if(e<30){
 if(!keys[k].used){keys[k].used=1;keys[k].key=key;trained++;}
 if(++freq[id]>freq[global_best])global_best=id;
 keys[k].total++;keys[k].hist[id]++;
 if(keys[k].hist[id]>keys[k].hist[keys[k].best])keys[k].best=id;
 }else {global_hit+=(id==global_best);if(!keys[k].used)return;
 key_only+=(id==keys[k].best && id!=global_best);global_only+=(id!=keys[k].best && id==global_best);
 known++;hit+=id==keys[k].best;
 if(keys[k].total>=8&&keys[k].hist[keys[k].best]==keys[k].total){mono++;mono_hit+=id==keys[k].best;}
 }
}
void phase_flip(unsigned f){
 mp_epoch=f;if(f==120)fprintf(stderr,"[MP_KEYS] paths=%u keys=%u late=%u known=%u matched=%u mono=%u mono_matched=%u global_matched=%u key_only=%u global_only=%u overflow=%u cross=%u\n",distinct,trained,late,known,hit,mono,mono_hit,global_hit,key_only,global_only,over,cross);
}
