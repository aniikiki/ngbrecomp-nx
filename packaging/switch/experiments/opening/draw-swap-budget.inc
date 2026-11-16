/* Adjacent game Present calls start/end a logical-work interval. Keep only
   whole intervals within the measured scene (ignore movie/menu Presents). */
static unsigned sb_flip,sb_prior_flip;
static uint64_t sb_prev_cpu,sb_prev_polls,sb_prev_entries;
static unsigned sb_hle_total,sb_prev_hle;
void cadence_swap(void){
 ++sw_total;
 if(sb_flip<30||sb_flip>=120){sb_prev_cpu=0;return;}
 uint64_t now=cadence_read(CLOCK_THREAD_CPUTIME_ID);
 unsigned h=sb_hle_total+correspondence_hle;
 if(sb_prev_cpu)fprintf(stderr,"[GAME_SWAP_COST] %u %u %u %llu %llu %llu\n",
 sb_prior_flip,sb_flip,h-sb_prev_hle,(unsigned long long)(now-sb_prev_cpu),
 (unsigned long long)(entries-sb_prev_entries),(unsigned long long)(ngb_guest_polls-sb_prev_polls));
 sb_prior_flip=sb_flip;sb_prev_cpu=now;sb_prev_hle=h;sb_prev_entries=entries;sb_prev_polls=ngb_guest_polls;
}
