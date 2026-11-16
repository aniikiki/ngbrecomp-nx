unsigned nb_window,nb_seq,nb_rand=123456789u,nb_controls,nb_samples;
unsigned long long nb_empty,nb_ticks;
unsigned long long nb_clock(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return t.tv_sec*1000000000ull+t.tv_nsec;}
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[NODE_BUDGET] %u %u %u %llu %u %llu\n",f,nb_seq,nb_samples,nb_ticks,nb_controls,nb_empty);
 if(!f||f==30){nb_seq=nb_samples=nb_controls=0;nb_ticks=nb_empty=0;}
 nb_window=f<120?f+1:0;
}
