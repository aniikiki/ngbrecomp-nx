unsigned mb_frame,mb_calls,mb_rng=2189709,mb_controls,mb_n,mb_cross;
unsigned long long mb_ticks,mb_empty;
unsigned long long mb_clock(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return t.tv_sec*1000000000ull+t.tv_nsec;}
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[MATRIX_BUDGET] %u calls=%u samples=%u ticks=%llu blanks=%u empty=%llu cross=%u\n",f,mb_calls,mb_n,mb_ticks,mb_controls,mb_empty,mb_cross);
 if(!f||f==30){mb_calls=mb_n=mb_controls=mb_cross=0;mb_ticks=mb_empty=0;}
 mb_frame=f<120?f+1:0;
}
