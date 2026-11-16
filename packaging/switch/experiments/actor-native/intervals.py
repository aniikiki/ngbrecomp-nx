"""Bound the cost of reproducing observable IRQ state without processing every
private instruction on the main thread. Counts byte writes per real interval,
not whole-frame time. Compare each interval to independently captured bytes."""
from pathlib import Path
import subprocess as sp,sys
s=sp.check_output([sys.executable,Path(__file__).with_name('journal-shadow.py')],text=True)
a='  for(unsigned q=0;q<ndue;q++){\n   while(cursor<nlog'
b='''  static uint8_t *marked;static uint32_t distinct[131072];if(!marked)marked=calloc(RAM,1);if(!marked)abort();
  unsigned unique=0,changed=0,runs=0;
  for(unsigned q=0;q<ndue;q++){unsigned touched=0;
   while(cursor<nlog'''
assert a in s;s=s.replace(a,b)
a='scratch[e[1]]=e[2];}'
b='''if(!marked[e[1]]){if(touched==131072)abort();marked[e[1]]=1;distinct[touched++]=e[1];}scratch[e[1]]=e[2];}
   for(unsigned x=0;x<touched;x++){unsigned a=distinct[x];if(!a||!marked[a-1])runs++;if(scratch[a]!=initial[a])changed++;}
   for(unsigned x=0;x<touched;x++){unsigned a=distinct[x];initial[a]=scratch[a];marked[a]=0;}unique+=touched;'''
# Maintain an independent prior-boundary image: final-output verification uses initial.
b=b.replace('initial[a]', 'previous[a]')
s=s.replace('static uint8_t*scratch;', 'static uint8_t*previous;if(!previous)previous=malloc(RAM);if(!previous)abort();memcpy(previous,initial,RAM);static uint8_t*scratch;')
assert a in s;s=s.replace(a,b);a='  fprintf(stderr,"[IRQ_MEMORY]';s=s.replace(a,'''  fprintf(stderr,"[IRQ_INTERVALS] id=%u checkpoints=%u unique=%u changed=%u runs=%u writes=%u\\n",id,ndue,unique,changed,runs,cursor);
'''+a);print(s)
