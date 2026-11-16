"""Extend the trained scene snapshot only after a rejected wave has joined.
No retries against live RAM; speculative results for the whole wave are
discarded on a miss. Only the next dispatch may see a newly learned page."""
def transform(s):
 s=s.replace('static unsigned planned[32768],np;', '''static unsigned planned[32768],np,misswaves,added;
static uint8_t known[32768];''')
 s=s.replace('if(hit)planned[np++]=pg;', 'if(hit){known[pg]=1;planned[np++]=pg;}')
 tag='for(unsigned u=1;u<count;u++)if(jobs[u].err)return 0;'
 assert s.count(tag)==1
 s=s.replace(tag,'''unsigned reject=0;
 for(unsigned u=1;u<count;u++)if(jobs[u].err){
  unsigned va=jobs[u].err,pg=(va&0x7fffffffu)>>12;reject=1;
  if(pos==1 && pg<32768 && !known[pg] && ngb_fast_page_bytes[va>>12]>(va&4095)){
   known[pg]=1;planned[np++]=pg;added++;}
 }
 if(reject){if(pos==1){misswaves++;fprintf(stderr,"[WAVE_MISS] frame=%u actual=%u pages=%u added=%u missed=%u errors=",frame,count,np,added,misswaves);
 for(unsigned u=1;u<count;u++)fprintf(stderr," %x",jobs[u].err);fputc(10,stderr);}return 0;}''')
 return s
