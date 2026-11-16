"""Set the CRT seed to zero in a temporary AArch64 host replay (never in a Switch NRO)."""
import re,struct,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1])
assert p.name=='replay' and p.parent.name=='host' and 'opening-present-combined' in p.parts
sym='ngb_reg_sub_0036E134'
dump=subprocess.check_output(['objdump','-d','--disassemble='+sym,str(p)],text=True)
matches=re.findall(r'^\s*([0-9a-f]+):\s+b9000014\s+str\s+w20, \[x0\]$',dump,re.M)
assert len(matches)==1 and len(re.findall(r'ldr\s+w20, \[x0\]',dump))==1
va=int(matches[0],16)
with p.open('r+b') as f:
 h=f.read(64);assert h[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',h,18)[0]==183
 off=struct.unpack_from('<Q',h,32)[0];size,n=struct.unpack_from('<HH',h,54)
 slots=[]
 for i in range(n):
  f.seek(off+i*size);typ,flags,fo,v,_,length,_,_=struct.unpack('<II6Q',f.read(56))
  if typ==1 and flags&1 and v<=va<=v+length-4:slots.append(fo+va-v)
 assert len(slots)==1
 f.seek(slots[0]);assert f.read(4)==bytes.fromhex('140000b9')
 f.seek(slots[0]);f.write(bytes.fromhex('1f0000b9')) # str wzr,[x0], preserving guest ECX
