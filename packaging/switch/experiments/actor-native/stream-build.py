"""Compact directly on the worker. Keep low-byte store masks and last values
within each poll; there is no byte trace to allocate or postprocess. One
unaligned store may touch several words. Only ordinary guest RAM is logged."""
from pathlib import Path
here=Path(__file__).resolve().parent;s=(here/'journal-build.py').read_text()
a=s.index("exec(compile(s,'worker-journal'")
s=s[:a]+'''s=s.replace("d=p/'opt050/actor-journal'","d=p/'opt050/actor-stream'")
s=s.replace('unsigned stride,events,nlog,','unsigned cnt;uint16_t slots[2048],usedslots[2048];uint32_t wordkeys[2048];uint8_t masks[2048];unsigned stride,events,nlog,')
a=s.index(' if(!ac.width)return;');b=s.index('ac.width=0;}',a)+len('ac.width=0;}')
s=s[:a]+"""
 for(unsigned i=0;i<ac.cnt;i++){unsigned at=ac.usedslots[i],addr=ac.wordkeys[at];
  if(ac.nlog>=524288){ac.error=~0u;longjmp(ac.unwind.escape,1);}
  uint32_t *e=ac.log+3*ac.nlog++;e[0]=(ac.events<<4)|ac.masks[at];e[1]=addr;__builtin_memcpy(e+2,ac.ram+addr,4);ac.slots[at]=0;
 }ac.cnt=0;}"""+s[b:]
s=s.replace('ac.nlog=ac.width=0;','ac.nlog=ac.cnt=0;__builtin_memset(ac.slots,0,sizeof ac.slots);')
s=s.replace('flush_store();ac.pending=a;ac.width=n;',"""
 while(n){unsigned w=a&~3u,lo=a&3,z=n<4-lo?n:4-lo,idx=((w>>2)*2654435761u)>>(32-11);
  while(ac.slots[idx] && ac.wordkeys[idx]!=w)idx=(idx+1)&2047;
  if(!ac.slots[idx]){if(ac.cnt>=2047){ac.error=~0u;longjmp(ac.unwind.escape,1);}
   ac.slots[idx]=1;ac.wordkeys[idx]=w;ac.masks[idx]=0;ac.usedslots[ac.cnt++]=idx;}
  ac.masks[idx]|=((1u<<z)-1u)<<lo;a+=z;n-=z;}
""")
'''+s[a:];exec(compile(s,'stream-worker-generator','exec'))
