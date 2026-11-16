unsigned fb_window,fb_rng=324151u,fb_counts[3][3];
unsigned long long fb_ns[3][2];
unsigned long long fb_clock(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return t.tv_sec*1000000000ull+t.tv_nsec;}
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<3;i++)fprintf(stderr,"[FAMILY_BUDGET] %u %u %u %u %llu %u %llu\n",f,i,fb_counts[i][0],fb_counts[i][1],fb_ns[i][0],fb_counts[i][2],fb_ns[i][1]);
 if(!f||f==30){memset(fb_counts,0,sizeof fb_counts);memset(fb_ns,0,sizeof fb_ns);}
 fb_window=f<120?f+1:0;
}
