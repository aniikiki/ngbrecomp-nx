static unsigned range_frame,range_n[15],range_equal[15],range_len[15];
void range_observe(unsigned slot,unsigned len,unsigned equal){
 if(!range_frame)return;
 if(slot>=15||(range_len[slot]&&range_len[slot]!=len))abort();
 range_n[slot]++;range_equal[slot]+=equal;range_len[slot]=len;
}
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<15;i++)
   fprintf(stderr,"[RANGE_CENSUS] %u %u %u %u %u\n",f,i,range_len[i],range_n[i],range_equal[i]);
 if(!f||f==30){memset(range_n,0,sizeof range_n);memset(range_equal,0,sizeof range_equal);}
 range_frame=f<120?f+1:0;
}
