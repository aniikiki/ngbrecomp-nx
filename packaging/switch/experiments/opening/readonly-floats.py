"""Test folding binary32 reads from aligned interior .rdata pages only.
Use the actual input XBE, never store derived literals in tracked files.
Experimental: fail the audit if the live float differs, and do not deploy
without establishing read-only protection against guest writes."""
from pathlib import Path
import sys,os,re,struct,math
root=Path('/work');base=root/'build/switch-runtime';abi=root/'packaging/switch/arm-registers'
sys.path.insert(0,str(root/'xboxrecomp/tools/abi_analysis'))
from xbe_min import XbeFile
xbe=XbeFile(root/'game_files/default.xbe')
sec,=[x for x in xbe.sections if x.name=='.rdata' and not x.flags&1]
lo=(sec.virtual_address+4095)&~4095
hi=(sec.virtual_address+min(sec.raw_size,sec.virtual_size))&~4095
audit='--audit' in sys.argv
d=base/'core-perf'/('opening-readonly-audit' if audit else 'opening-readonly')
d.mkdir(exist_ok=True);os.environ['NGB_REG_OUT']=str(d)
seen=set();sites=0
for unit in (0,1,2,3,9,10,11,14,16,27,28,29,37,44):
 name=f'recomp_{unit:04}.c'
 lines=[]
 for l in (base/'gen'/name).read_text().splitlines(True):
  # Only reads in known generator contexts, never an address or destination.
  def fold(m):
   global sites
   va=int(m[2],16)
   if va%4 or not lo<=va<=hi-4:return m[0]
   data=xbe.read_bytes_at_va(va,4,'.rdata');val=struct.unpack('<f',data)[0]
   if not math.isfinite(val):return m[0]
   bits=int.from_bytes(data,'little');seen.add(va);sites+=1
   expr=val.hex()+'f'
   if audit:expr=f'({{float live_=MEMF({m[2]});uint32_t bits_;__builtin_memcpy(&bits_,&live_,4);if(bits_!=0x{bits:x}u)__builtin_trap();live_;}})'
   return m[1]+expr
  lines.append(re.sub(r'( = |XMM_SCALAR\(|\(double\)| [*+/\-] )MEMF\((0x[\da-fA-F]+)\)',fold,l))
 (d/name).write_text(''.join(lines))
print('eligible read sites',sites,'distinct aligned .rdata floats',len(seen),file=sys.stderr,flush=True)
s=(abi/'compile.py').read_text()
k=' sp.run(c,cwd=w,check=True)';assert s.count(k)==1
s=s.replace(k," c[-1]=str(o/n)\n"+k)
exec(compile(s,'readonly-abi','exec'),{})
exec(compile((abi/'gates.py').read_text(),'readonly-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
for f in d.glob('recomp_*.c'):f.unlink()
