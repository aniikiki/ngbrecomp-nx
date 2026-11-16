"""Capture a few exact isolated actor jobs once, for rapid worker iteration
without replaying the entire title and combat. Private locally, never distribute."""
from pathlib import Path
import subprocess as sp,sys
d=Path(__file__).resolve().parent;s=sp.check_output([sys.executable,d/'shadow.py'],text=True)
s=(d/'gz-abi.h').read_text()+'\n'+s
s=s.replace('static uint64_t ticks,ent;', 'static uint8_t inregs[512];static unsigned sequence;static uint64_t ticks,ent;')
s=s.replace('nr=fork_regs(outregs,&e0);','nr=fork_regs(outregs,&e0);memcpy(inregs,outregs,nr);')
s=s.replace('if(s && frame>=1802 && frame<=1810 && (i==0||i==21||i==4||i==7))','if(s && frame>=1802 && sequence<8 && (i==0||i==21||i==4||i==7))')
a='  for(unsigned j=0;j<num;j++)seen[written[j]]=0;'
s=s.replace(a,'''  char fn[256];snprintf(fn,sizeof fn,"/work/build/switch-runtime/opt050/actor-native/job%02u.gz",sequence++);gzFile file=gzopen(fn,"wb1");if(!file)abort();
  uint32_t meta[]={0x4e474241,frame,id,nr,num,initial_sp};uint64_t timing[]={p0,e0};
  if(gzwrite(file,meta,sizeof meta)!=sizeof meta || gzwrite(file,timing,sizeof timing)!=sizeof timing ||
   gzwrite(file,inregs,nr)!=(int)nr || gzwrite(file,regs,nr)!=(int)nr || gzwrite(file,pages,2u<<20)!=(2u<<20) ||
   gzwrite(file,initial,RAM)!=RAM)abort();
  for(unsigned j=0;j<num;j++){unsigned at=written[j];if(gzwrite(file,&at,4)!=4||gzwrite(file,base+at,1)!=1)abort();}
  if(gzclose(file)!=Z_OK)abort();
'''+a)
print(s)
