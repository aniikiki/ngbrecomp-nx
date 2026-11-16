"""Exact symbol relocations in original private objects, mapped to sampled NRO PCs.
Nearby arithmetic is not counted. Run inside the devkit image."""
from pathlib import Path
import collections,re,subprocess,json,hashlib
base=Path('build/switch-runtime');regs=base/'native-regs';rel=base/'history/0.51.0-rc1'
t='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-'
def tool(k,*args):return subprocess.check_output([t+k,*args],text=True)
elf=regs/'ngb-startup.elf'
img=(rel/'ngb-startup.nro').read_bytes()
assert hashlib.sha256(img).hexdigest()==json.loads((rel/'deployment.json').read_text())['sha256']
assert img[64:84].hex()==re.search(r'Build ID: (\w+)',tool('readelf','-n',elf))[1]
symbols={k:(int(a,16),int(n,16)) for a,n,k in re.findall(r'^(\w+) (\w+) [tT] (\S+)$',tool('nm','-S',elf),re.M)}
pairs=collections.defaultdict(list)
for row in (base/'core-perf/opening-setup/leaf-budget.tsv').read_text().splitlines():
 r=row.split('\t')
 if len(r)>=7 and 1<=int(r[0])<=120:pairs[r[3]].append((int(r[0]),int(r[2],16)))
targets={k:int(a,16) for a,k in re.findall(r'^(\w+) [bBdD] (ngb_guest_polls|ngb_pending_dpcs|ngb_poll_mask)$',tool('nm',elf),re.M)}
assert len(targets)==3
keys={};counts=collections.Counter();parts=collections.Counter()
objdir=base/'switch/CMakeFiles/ngb_boot_code.dir/work/build/switch-runtime/gen'
private=list(regs.glob('recomp_*.c.o'));units={f.name.split('.')[0] for f in private}
public=[f for f in objdir.glob('recomp_*.o') if f.stem not in units and re.fullmatch(r'recomp_\d{4}',f.stem)]
assert len(private)==14 and len(public)==33
for obj in private+public:
 sec='';interested={};raw={}
 obj_symbols={n for n in pairs if n.startswith('ngb_reg_')==(obj in private)}
  # Disassemble only sections actually sampled in this object (especially for
  # public objects containing debug data). Avoid scanning full guest text.
 candidates=set(re.findall(r'^\s*\d+ (\.text\.\S+)\s',tool('objdump','-h',obj),re.M))
 sections=[x for x in candidates if ('ngb_reg_' if obj in private else '')+x[6:] in obj_symbols]
 if not sections:continue
 for line in tool('objdump','-dr',*[arg for section in sections for arg in ('-j',section)],obj).splitlines():
  if line.startswith('Disassembly of section '):
   sec=line[23:-1];name=('ngb_reg_' if obj in private else '')+sec.removeprefix('.text.')
   interested={};raw={}
   if name not in pairs or name not in symbols:continue
   start,size=symbols[name]
   interested={pc-start:pc for f,pc in pairs[name] if start<=pc<start+size}
   if interested:target_start=start
  if not interested:continue
  ins=re.match(r'^\s*([a-f0-9]+):\s+([a-f0-9]{8})\s+(\S+)',line)
  if ins:raw[int(ins[1],16)]=(int(ins[2],16),ins[3]);continue
  m=re.match(r'^\s*([a-f0-9]+): R_AARCH64_(\S+)\s+(ngb_guest_polls|ngb_poll_mask|ngb_pending_dpcs)(?:\s|$)',line)
  if not m:continue
  off=int(m[1],16)
  if off not in interested and off-4 not in interested:continue
  pc=target_start+off;op,kind=raw[off]
  # Exclude link-time opcode relaxation; for the supported relocation verify
  # all non-relocatable bits against the shipped executable.
  mask=(0x60ffffe0 if m[2]=='ADR_PREL_PG_HI21' else 0x003ffc00 if m[2].startswith(('LDST','ADD_ABS_LO12')) else None)
  if mask is None:continue
  word=int.from_bytes(img[pc:pc+4],'little')
  if ((word^op)&~mask)!=0:continue
  target=targets[m[3]]
  if kind=='adrp':
   imm=((word>>29)&3)|(((word>>5)&0x7ffff)<<2)
   if imm&(1<<20):imm-=1<<21
   if (pc>>12)+imm!=target>>12:continue
  elif kind in ('ldr','str','add'):
   scale=0 if kind=='add' else word>>30
   if (((word>>10)&4095)<<scale)!=(target&4095):continue
  else:continue
  keys[pc]=(m[3],kind)
  # An unchanged ADD xT,xT,#1 immediately feeding the relocated STR xT.
  if m[3]=='ngb_guest_polls' and kind=='str' and off>=4:
   reg=op&31;expected=0x91000400|(reg<<5)|reg
   if raw.get(off-4,(None,None))[0]==expected==int.from_bytes(img[pc-4:pc],'little'):keys[pc-4]=(m[3],'add')
for group,rows in pairs.items():
 for f,pc in rows:
  window=30 if f<=30 else 120;counts[window]+=1
  if pc in keys:parts[window,keys[pc]]+=1
for w,n in sorted(counts.items()):
 hits={k:v for (x,k),v in parts.items() if x==w}
 print('window end',w,'all samples',n,'confirmed poll instructions',sum(hits.values()),hits)
