"""Count completed retirement groups and distribution without timing or changing parsing."""
def transform(s):
 k='    packet_count += packets;\n    param_count += used - packets;';assert s.count(k)==1
 return 'extern unsigned fg_on;extern void fg_group(unsigned,unsigned);\n'+s.replace(k,'    if(fg_on)fg_group(packets,used);\n'+k)
counters=r"""
unsigned fg_on;
static unsigned long long fg_groups,fg_packets,fg_words,fg_bins[6];
void fg_group(unsigned n,unsigned words){
 if(!n||words<=n)abort();
 fg_groups++;fg_packets+=n;fg_words+=words;
 fg_bins[n==1?0:n==2?1:n<=4?2:n<=8?3:n<=16?4:5]++;
}
void phase_flip(unsigned f){
 if(f==30||f==120){fprintf(stderr,"[FIFO_GROUPS] %u %llu %llu %llu",f,fg_groups,fg_packets,fg_words);for(unsigned i=0;i<6;i++)fprintf(stderr," %llu",fg_bins[i]);fputc(10,stderr);}
 if(!f||f==30){fg_groups=fg_packets=fg_words=0;memset(fg_bins,0,sizeof fg_bins);}
 fg_on=f<120;
}
"""
