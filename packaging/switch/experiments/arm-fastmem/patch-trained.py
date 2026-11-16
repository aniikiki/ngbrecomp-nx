"""Offline host ELF only. Permanently use the original checked helper at
fault-prone sites; every other site's mapping/protection recovery stays intact."""
from pathlib import Path
from struct import unpack_from,pack_into
import re,sys
binary,log,out=map(Path,sys.argv[1:])
s=log.read_text();assert ('verified original combat window' in s or '[RESULT] status=1 reason=verified 120 original demo frames' in s) and not out.exists()
rows=[(int(pc,16),int(slow,16),int(n)) for pc,slow,n in re.findall(r'^\[SLOW_SITE\] ([a-f0-9]+) ([a-f0-9]+) (\d+)$',s,re.M)]
assert rows and sum(n for _,_,n in rows)==int(re.search(r'recovered_faults=(\d+)',s)[1])
data=bytearray(binary.read_bytes());assert data[:6]==b'\x7fELF\x02\x01' and unpack_from('<H',data,18)[0]==183
phoff=unpack_from('<Q',data,32)[0];ents,count=unpack_from('<HH',data,54);loads=[]
for i in range(count):
 typ,flags,offset,va,pa,fs,ms,align=unpack_from('<IIQQQQQQ',data,phoff+i*ents)
 if typ==1 and flags&1:loads.append((va,va+fs,offset))
for pc,slow,n in rows:
 # Registered fixup table emitted by the same binary's asm goto. Validate
 # disassembly before replacing its one instruction with a local branch.
 v,e,o=next(r for r in loads if r[0]<=pc<r[1] and r[0]<=slow<r[1])
 ins,=unpack_from('<I',data,o+pc-v);assert ins&0x3b200c00==0x38200800,hex(ins)
 delta=slow-pc;assert delta%4==0 and -(1<<27)<=delta<1<<27
 pack_into('<I',data,o+pc-v,0x14000000|((delta//4)&0x3ffffff))
out.write_bytes(data);out.chmod(0o755);print('redirected',len(rows),'sites accounting for',sum(n for _,_,n in rows),'recoveries',flush=True)
