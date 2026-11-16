"""Keep raw counters in RAM during the opening; format after validation only."""
import re
def transform(s):
 k='static unsigned pm_active';assert s.count(k)==1
 s=s.replace(k,r'''struct bp {unsigned a,b,c;unsigned long long n,h,t,e,p;};
static struct bp bp_rows[144],bf_rows[121];
static unsigned bp_count;
static void bp_record(unsigned a,unsigned b,unsigned c,unsigned long long n,unsigned long long h,unsigned long long t,unsigned long long e,unsigned long long p){
 if(bp_count==144){abort();}bp_rows[bp_count++]=(struct bp){a,b,c,n,h,t,e,p};}
static void bp_dump(void){
 for(unsigned i=0;i<bp_count;i++){struct bp v=bp_rows[i];fprintf(stderr,"[PRESENT_MIX] %u %u %u %llu %016llx %llu %llu %llu\n",v.a,v.b,v.c,v.n,v.h,v.t,v.e,v.p);}
 for(unsigned i=1;i<=120;i++){struct bp v=bf_rows[i];if(v.a!=i)abort();fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n[OPEN_WORK] %u %llu %llu\n",i,v.b,v.t,v.c,i,v.e,v.p);}}
'''+k)
 s,n=re.subn(r'fprintf\(stderr,"\[PRESENT_MIX\] [^"]+",pm_prev_f','bp_record(pm_prev_f',s);assert n==1
 a=s.index('    if(f && previous_ns)fprintf');b=s.index('    prev_ent=',a)
 s=s[:a]+'''    static uint64_t prev_ent,prev_poll;
    if(f && previous_ns && f<=120)bf_rows[f]=(struct bp){f,cache_active,draws-previous_draws,0,0,now-previous_ns,entries-prev_ent,ngb_guest_polls-prev_poll};
'''+s[b:]
 k='ngb_stop("verified 120 original demo frames", 120);';assert s.count(k)==1
 return s.replace(k,'{ bp_dump(); '+k+' }')
