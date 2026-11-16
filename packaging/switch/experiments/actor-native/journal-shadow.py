"""Check writes visible to the IRQ at the moment the original enters it,
not just the final write of each job. The reference and trace never share RAM."""
from pathlib import Path
import subprocess as sp,sys
s=sp.check_output([sys.executable,Path(__file__).with_name('checkpoint-shadow.py')],text=True)
s=s.replace('uint8_t*,unsigned,unsigned*);','uint8_t*,unsigned,unsigned*,uint32_t*,unsigned*);')
s=s.replace('static unsigned events,ndue,counting;', '''static unsigned events,ndue,counting;
static uint32_t write_log[524288][3],nlog;static unsigned first[8193],nref,refaddr[4000000];static uint8_t refvalue[4000000];
static void save_boundary(void);
''').replace('at[ndue]=charged','save_boundary();at[ndue]=charged').replace('520,&events);','520,&events,write_log[0],&nlog);').replace('charged=ndue=events=0;', 'charged=ndue=events=nref=0;')
a=s.index('void dep_bind(void*p)')
s=s[:a]+'''static void save_boundary(void){first[ndue]=nref;if(nref+num>4000000)abort();
 for(unsigned j=0;j<num;j++){refaddr[nref]=written[j];refvalue[nref++]=base[written[j]];}}
'''+s[a:]
a=s.index('  unsigned boundary_err=0;')
s=s[:a]+'''  first[ndue]=nref;unsigned cursor=0,bad_mem=0,bad_boundaries=0;
  for(unsigned q=0;q<ndue;q++){
   while(cursor<nlog && write_log[cursor][0]<at[q]){uint32_t *e=write_log[cursor++];initial[e[1]]=e[2];}
   unsigned bad=0;for(unsigned k=first[q];k<first[q+1];k++){unsigned a=refaddr[k];if(initial[a]!=refvalue[k]){
    if(!bad_mem&&!bad)fprintf(stderr,"[IRQ_MEMORY_DIFF] id=%u t=%u a=%08x got=%02x want=%02x\\n",id,at[q],a,initial[a],refvalue[k]);bad++;}}
   bad_mem+=bad;bad_boundaries+=!!bad;
  }
  fprintf(stderr,"[IRQ_MEMORY] id=%u boundaries=%u bad=%u bytes=%u diff=%u journal=%u\\n",id,ndue,bad_boundaries,nref,bad_mem,nlog);
'''+s[a:]
# Verify extra output against a pristine image in shadow.py. Reverse the
# diagnostic replay by using a separate scratch image (copy_ is final output).
s=s.replace('first[ndue]=nref;unsigned cursor','static uint8_t*scratch;if(!scratch)scratch=malloc(RAM);if(!scratch)abort();memcpy(scratch,initial,RAM);first[ndue]=nref;unsigned cursor')
s=s.replace('initial[e[1]]=e[2]', 'scratch[e[1]]=e[2]').replace('initial[a]!=refvalue[k]', 'scratch[a]!=refvalue[k]').replace('a,initial[a],refvalue[k]', 'a,scratch[a],refvalue[k]')
print(s)
