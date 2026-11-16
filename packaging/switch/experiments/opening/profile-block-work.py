"""Recover frequency-weighted generated basic-block work from existing opening PGO data.
Only accept GCC's verified profile; place compiler dumps in an ephemeral directory."""
from pathlib import Path
import re,shlex,tempfile,subprocess,sys,struct
from collections import Counter,defaultdict
base=Path('/work/build/switch-runtime')
d=base/'core-perf/opening-register-pgo'
cmds=subprocess.check_output(['ninja','-t','commands','ngb-startup'],cwd=base/'switch',text=True).splitlines()
def inspect(unit):
 name=f'recomp_{unit:04}.c'
 c=next(shlex.split(x) for x in cmds if x.endswith('/'+name))
 with tempfile.TemporaryDirectory() as tmp:
  t=Path(tmp);c[c.index('-o')+1]=str(d/(name+'.native.s'))
  c[c.index('-MF')+1]=str(t/'deps');c[c.index('-c')]='-S'
  c[1:1]=['-I'+str(d),'-include',str(d/'regs.h')]
  c[-1:-1]=['-g0','-ffixed-x28','-fno-ipa-ra','-fno-optimize-sibling-calls','-fprofile-dir='+str(d/'profiles'),'-fprofile-use','-fno-profile-values','-fprofile-partial-training','-Werror=missing-profile','-Werror=coverage-mismatch','-fno-reorder-blocks-and-partition','-fno-ipa-cp-clone','-dA']
  # The bare-metal emitter produced individual streams, not finalized host profiles.
  # Feed a filename record and untouched gcda bytes to the matching GCC merge tool.
  original,=(d/'profiles').rglob(name+'.native.gcda')
  dst=t/'profiles'/original.relative_to(d/'profiles')
  dst.parent.mkdir(parents=True); filename=bytes(str(dst),'utf8')+bytes(1);data=original.read_bytes()
  stream=struct.pack('<I',0x6763666e)+data[4:8]+struct.pack('<I',len(filename))+filename+data
  subprocess.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcov-tool','merge-stream'],input=stream,check=True)
  assert dst.is_file()
  c[c.index('-fprofile-dir='+str(d/'profiles'))]='-fprofile-dir='+str(t/'profiles')
  asm=d/(name+'.native.s')
  assert not asm.exists()
  try:
   subprocess.run(c,cwd=base/'switch',check=True)
   byfn=Counter(); byclass=Counter(); quality=Counter();counts=Counter()
   fn=None; weight=0
   for l in asm.read_text().splitlines():
    if m:=re.fullmatch(r'(\w+):',l):
     fn=m[1];weight=0
    if l.lstrip().startswith('.size'):fn=None;weight=0
    if m:=re.match(r'// BLOCK \d+, count:(\d+)(.*?) seq:',l):
     q=m[2].strip() or 'unqualified'
     quality[q]+=1;weight=int(m[1]) if q in ('unqualified','(precise)') else 0
     continue
    if not fn or not weight:continue
    m=re.match(r'^\s+([a-z][a-z0-9.]*)\s*(.*)',l)
    if not m:continue
    op,args=m.groups()
    cat=('page-table-read' if op.startswith('ld') and '[x27,' in args else 'host-stack' if op.startswith(('ld','st')) and ('[sp' in args or '[x29' in args) else 'load' if op.startswith('ld') else 'store' if op.startswith('st') else 'call' if op in ('bl','blr') else 'other')
    byfn[fn]+=weight;byclass[cat]+=weight;counts[fn,cat]+=weight
   print('unit',unit,'block counts by GCC quality',quality,'weighted static instructions',sum(byfn.values()),flush=True)
   print('work',byclass,'leaders',byfn.most_common(8),flush=True)
   if not byfn:
    blob=asm.read_text().split('sub_00308BF0:',1)[-1]
    print('actual hot routine',blob[:1600],flush=True)
   assert byfn,'no measured counts; do not rank guessed paths'
   for (fn,cat),n in counts.items():print('ROW',unit,fn,cat,n)
  finally:asm.unlink(missing_ok=True)
for n in sys.argv[1:]:inspect(int(n))
