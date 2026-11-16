"""Train and use GCC profiles on the actual full-page/private-register ABI. No changes to production objects."""
from pathlib import Path
import sys,os,re,subprocess as sp,shutil,struct
p=Path(__file__).resolve().parent; abi=p.parents[1]/'arm-registers'
d=Path('/work/build/switch-runtime/core-perf/opening-retained-pgo');d.mkdir(exist_ok=True)
mode=sys.argv[1];assert mode in ('train','use','local','local-train','extra-train','extra-use')
extra=mode.startswith('extra-')
if extra:
 mode=mode[6:];d=d.parent/'opening-extra-partition';d.mkdir(exist_ok=True)
local=mode.startswith('local')
if local:
 mode='train' if mode=='local-train' else 'use'
 d=d.parent/'opening-retained-pgo-local';d.mkdir(exist_ok=True)
units=[0,1,9,15,26] if extra else [2,10,16,28,29];names=[f'recomp_{u:04}.c' for u in units]
cc='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc';profile=d/'profiles'/str(d).lstrip('/')
profile.mkdir(parents=True,exist_ok=True)
for n in names:
 f=profile/(n+'.native.gcda')
 if mode=='train':
  if f.exists():raise RuntimeError('profile already exists: '+str(f))
 else:
  backup=f.with_suffix('.raw')
  if backup.exists():
   merged=f.read_bytes();original=backup.read_bytes()
   assert merged[:16]==original[:16] and merged[16:20]==struct.pack('<I',0xa1000000) and merged[32:]==original[16:]
   continue
  raw=f.read_bytes();assert raw[:4]==b'adcg' and b'\x00\x00\x00\xa1'!=raw[16:20]
  # Merge to a fresh sibling (don't merge a stream on top of itself).
  dest=f.with_suffix('.new.gcda');assert not dest.exists();fn=os.fsencode(dest)+b'\0'
  sp.run([cc.replace('gcc','gcov-tool'),'merge-stream'],input=struct.pack('<I',0x6763666e)+raw[4:8]+struct.pack('<I',len(fn))+fn+raw,check=True)
  assert dest.read_bytes()[16:20]==struct.pack('<I',0xa1000000)
  f.rename(f.with_suffix('.raw'));dest.rename(f)
os.environ.update(NGB_REG_OUT=str(d),NGB_REG_PROFILE=mode)
s=(abi/'compile.py').read_text().split("f=o/'entry.S'")[0].replace("(r/'guest_memory.h').read_text()",repr((d.parent/'opening-full-page/template.h').read_text())).replace('register uint16_t *reg_pages asm("x27");','register uint32_t *reg_ends asm("x27");').replace('#define ngb_fast_page_bytes reg_pages','')
s,c=re.subn(r'^ns=\[[\d,]+\]$','ns=list(range(47))',s,flags=re.M);assert c==1
s=s.replace(r'(?:sub_|d3d_orig_)[0-9A-F]+',r'(?:(?:sub_|d3d_orig_)[0-9A-F]+|xbe_entry_point)').replace('ex.map(build,units)','ex.map(build,'+repr(names)+')')
s=s.replace(' sp.run(c,cwd=w,check=True)',""" if n in ('recomp_0002.c','recomp_0010.c','recomp_0016.c','recomp_0026.c'):c[-1:-1]=['-O3','-fno-peel-loops','-fno-loop-unroll-and-jam','--param=max-completely-peel-times=0','-ffp-contract=off','-fno-fast-math','-fno-optimize-sibling-calls']
 sp.run(c,cwd=w,check=True)""")
if local:
 k=' sp.run(c,cwd=w,check=True)'
 assert s.count(k)==1
 s=s.replace(k," c[-1:-1]=['-fno-semantic-interposition']\n"+k)
if extra and mode=='use':
 assert s.count('-fno-reorder-blocks-and-partition')==1
 s=s.replace('-fno-reorder-blocks-and-partition','-freorder-blocks-and-partition')
exec(compile(s,'retained-pgo','exec'),{})
assert (d/'guest_memory.h').read_bytes()==(d.parent/'opening-full-page/guest_memory.h').read_bytes()
exec(compile((abi/'gates.py').read_text(),'retained-gates','exec'),{})
if mode=='train':
 for u,n in zip(units,names):
  obj=d/(n+'.o');src=d/(n+'.gated.s')
  rows=sp.check_output([cc.replace('gcc','nm'),'-S',obj],text=True).splitlines()
  arcs=[(v[3],int(v[1],16)) for l in rows if len(v:=l.split())==4 and v[3].startswith('__gcov0.')]
  assert arcs and all(0<size//8<65536 and size%8==0 for _,size in arcs)
  with src.open('a') as f:
   f.write(f'\n.text\n.global clear_retained_{u}\nclear_retained_{u}:\n')
   for label,size in arcs:f.write(f'adrp x9,{label}\nadd x9,x9,:lo12:{label}\nmov x10,#{size//8}\n1: str xzr,[x9],#8\nsubs x10,x10,#1\nb.ne 1b\n')
   f.write('ret\n')
  sp.run([cc,'-c',src,'-o',obj],check=True)
 shutil.copyfile(sp.check_output([cc,'-print-file-name=libgcov.a'],text=True).strip(),d/'gcov.a')
for f in d.glob('recomp_*.s'):f.unlink()
