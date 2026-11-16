
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
static unsigned ab_window,ab_random=1719,ab_calls,ab_emptyvoices,ab_paused,ab_samples,ab_controls;
static uint64_t ab_ticks,ab_blanks;
static uint64_t ab_clock(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
void ngb_audio_poll(void){
 if(!ab_window){original_audio_poll();return;}
 ab_calls++;ab_emptyvoices+=!(active_voices[0]|active_voices[1]|active_voices[2]|active_voices[3]);
 ab_paused+=!!voice_engine_paused;
 ab_random=1664525u*ab_random+1013904223u;unsigned pick=ab_random>>27;
 if(!pick){uint64_t a=ab_clock();original_audio_poll();ab_ticks+=ab_clock()-a;ab_samples++;}
 else{if(pick==1){uint64_t a=ab_clock();ab_blanks+=ab_clock()-a;ab_controls++;}original_audio_poll();}
}
void audio_budget_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[AUDIO_BUDGET] %u %u %u %u %u %llu %u %llu\n",f,ab_calls,ab_emptyvoices,ab_paused,ab_samples,(unsigned long long)ab_ticks,ab_controls,(unsigned long long)ab_blanks);
 if(!f||f==30){ab_calls=ab_emptyvoices=ab_paused=ab_samples=ab_controls=0;ab_ticks=ab_blanks=0;}
 ab_window=f<120;
}
