unsigned ms_on;
static unsigned long long ms_runs,ms_total,ms_ok,ms_saved;
void ms_group(unsigned va,unsigned len,unsigned ops){
 ms_runs++;ms_total+=ops;
 if((va&4095)+len<=ngb_fast_page_bytes[va>>12]){ms_ok++;ms_saved+=ops-1;}
}
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[MIXED_SPAN] %u %llu %llu %llu %llu\n",f,ms_runs,ms_total,ms_ok,ms_saved);
 if(!f||f==30){ms_runs=ms_total=ms_ok=ms_saved=0;}ms_on=f<120;
}
