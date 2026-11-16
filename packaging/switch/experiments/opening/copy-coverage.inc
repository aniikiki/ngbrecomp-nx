unsigned pc_active,pc_total,pc_hit,pc_same;
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[COPY_COVERAGE] %u total=%u fast=%u equal=%u\n",f,pc_total,pc_hit,pc_same);
 if(!f||f==30)pc_total=pc_hit=pc_same=0;
 pc_active=f<120;
}
