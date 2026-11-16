"""Map sampled retained PCs to the same baseline objects; compare only static counts on candidate."""
import re,subprocess,bisect
from collections import Counter
from pathlib import Path
root=Path('build/switch-runtime/core-perf')
d=root/'opening-after-profile'
syms={}
for line in (d/'symbols.txt').read_text().splitlines():
 a,n,_,name=line.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>syms.get(a,(0,''))[0]:syms[a]=(n,name)
keys=sorted(syms)
samples=Counter()
for i in range(1,5):
 log=(d/f'run-{i}.log').read_text()
 assert 'reason=verified 120 original demo frames' in log
 for f,pc in re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',log,re.M):
  if not 31<=int(f)<=120:continue
  pc=int(pc,16);j=bisect.bisect_right(keys,pc)-1
  if j<0:continue
  a=keys[j];n,name=syms[a]
  if pc<a+n:samples[name,pc-a]+=1
def inspect(group):
 cnt=Counter()
 for u in (2,10,16,26,39):
  obj=root/group/f'recomp_{u:04}.c.o'
  name=None
  p=subprocess.Popen(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objdump','-d',obj],stdout=subprocess.PIPE,text=True)
  for line in p.stdout:
   m=re.match(r'^([0-9a-f]+) <([^>]+)>:',line)
   if m:name=m[2];start=int(m[1],16);continue
   if not name or not name.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):continue
   m=re.match(r'^\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(\w+)\s*(.*)',line)
   if not m:continue
   stack=m[2].startswith(('ld','st')) and bool(re.search(r'\[(?:sp|x29)(?:\]|,)',m[3]))
   cnt['instructions']+=1;cnt['sp/fp memory instructions']+=stack
   if group=='opening-page-hot-o3':
    hits=samples[name,int(m[1],16)-start];cnt['sampled']+=hits;cnt['sampled sp/fp memory']+=hits*stack
  assert p.wait()==0
 print(group,dict(cnt),flush=True)
if __name__=='__main__':
 import sys
 for group in sys.argv[1:]:inspect(group)
