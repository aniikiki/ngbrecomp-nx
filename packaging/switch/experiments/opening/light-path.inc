unsigned lp_on,lp_calls[8];
void phase_flip(unsigned f){
 if(f==30||f==120){fprintf(stderr,"[LIGHT_PATH] %u",f);for(unsigned i=0;i<8;i++)fprintf(stderr," %u",lp_calls[i]);fputc(10,stderr);}
 if(!f||f==30)memset(lp_calls,0,sizeof lp_calls);
 lp_on=f<120;
}
