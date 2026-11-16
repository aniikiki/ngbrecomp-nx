unsigned np_active,np_used,np_q[256][3],np_v[256][128][3];
void phase_flip(unsigned f){
 if(np_active){
   unsigned attempts=0,equal=0,length=0,bad=0,changed=0;
   if(np_used>256)abort();
   for(unsigned q=0;q<np_used;q++){
     unsigned n=np_q[q][2];if(n>128)abort();
     for(unsigned i=1;i<n;i++)if(np_v[q][i-1][2]!=np_v[q][i][0])bad++;
     for(unsigned j=q;j--;){
       if(np_q[q][0]!=np_q[j][0])continue;
       unsigned m=np_q[j][2];
       if(m && n>m && np_q[q][1]>np_q[j][1]){
         attempts++;
         unsigned i=0;
         for(;i<m;i++)if(np_v[q][i][0]!=np_v[j][i][0] ||
           np_v[q][i][1]!=np_v[j][i][1] || (i+1<m && np_v[q][i][2]!=np_v[j][i][2]))break;
         if(i==m){equal++;length+=m;}else changed++;
       }
       break;
     }
   }
   fprintf(stderr,"[NODE_PREFIX] %u %u %u %u %u %u %u\n",f,np_used,attempts,equal,changed,length,bad);
 }
 np_active=(f==0||f==29||f==30||f==59||f==89||f==119);
 np_used=0;if(np_active)memset(np_q,0,sizeof np_q);
}
