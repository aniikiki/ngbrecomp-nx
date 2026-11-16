"""Classify delivered guest PCs by actual opcode/operands in the selected unit."""
import runpy,re,subprocess,collections
from pathlib import Path
q=runpy.run_path(str(Path(__file__).with_name('ira-audit.py')))
samples=q['samples'];root=q['root']
stats=collections.Counter(); lines=collections.defaultdict(collections.Counter)
for u in range(47):
 group='opening-page-hot-o3' if u in (2,10,16,26,39) else 'opening-full-page'
 obj=root/group/f'recomp_{u:04}.c.o'
 args=['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objdump','-d',obj]
 proc=subprocess.Popen(args,stdout=subprocess.PIPE,text=True)
 wanted={};start=0
 for line in proc.stdout:
  if line.endswith('>:\n'):
   m=re.match(r'^([0-9a-f]+) <([^>]+)>:',line)
   wanted={};start=0
   if m and m[2].startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):
    fn=m[2];start=int(m[1],16);wanted=byname.get(fn,{}) if 'byname' in globals() else {}
    if 'byname' not in globals():
     byname=collections.defaultdict(dict)
     for (k,o),v in samples.items():byname[k][o]=v
     wanted=byname.get(fn,{})
   continue
  if not wanted or ':' not in line:continue
  a=line.partition(':')[0].strip()
  if not re.fullmatch('[0-9a-f]+',a):continue
  n=wanted.get(int(a,16)-start,0)
  if not n:continue
  m=re.match(r'^\s*[0-9a-f]+:\s+[0-9a-f]{8}\s+(\S+)\s*(.*)',line);assert m
  op,operand=m.groups();mem=op.startswith(('ld','st'))
  if mem and '[x27' in operand:category='page-table access'
  elif mem and '[x26' in operand:category='direct RAM access'
  elif mem and re.search(r'\[(?:sp|x29)(?:\]|,)',operand):category='native stack access'
  elif mem:category='other load/store'
  elif op.startswith('b.') or op.startswith(('cb','tb')):category='conditional branch'
  elif op in ('b','bl','blr','br','ret'):category='call/jump/return'
  elif op in ('adrp','adr'):category='address formation'
  elif op.startswith('f'):category='floating-point'
  else:category='remaining'
  stats[category]+=n;lines[category][op+' '+operand]+=n
 assert proc.wait()==0
print('matched',sum(stats.values()),stats)
for k in stats:print(k,lines[k].most_common(3))
