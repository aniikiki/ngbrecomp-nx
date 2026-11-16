unsigned rr_fixed;
static unsigned rr_sets,rr_total,rr_last,rr_since;
static uint64_t rr_hash=14695981039346656037ull;
__attribute__((constructor)) static void rr_init(void){rr_fixed=getenv("NGB_REPLAY_FIXED_SEED")!=NULL;}
void rr_set(unsigned v){rr_sets++;rr_last=v;}
void rr_observe(unsigned v){rr_total++;if(pm_active){rr_since++;rr_hash=(rr_hash^v)*1099511628211ull;}}
static void rr_present(void){
 if(pm_active)fprintf(stderr,"[RNG_PRESENT] %u %u %u %u %u %u %016llx\n",pm_fifo,rr_fixed,rr_sets,rr_last,rr_total,rr_since,(unsigned long long)rr_hash);
 rr_since=0;rr_hash=14695981039346656037ull;
}
