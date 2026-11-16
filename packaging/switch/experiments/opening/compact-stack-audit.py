"""Look up each sampled compact guest PC in its object and classify SP-relative traffic."""
import bisect, re, subprocess
from pathlib import Path
from collections import Counter,defaultdict
root=Path('build/switch-runtime/core-perf');d=root/'opening-compact-profile'
syms={}
for l in (d/'symbols.txt').read_text().splitlines():
 a,n,_,fn=l.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>syms.get(a,(0,''))[0]:syms[a]=(n,fn)
keys=sorted(syms);wanted=defaultdict(Counter)
for i in range(1,5):
 s=(d/f'run-{i}.log').read_text();assert 'reason=verified 120 original demo frames' in s
 for f,pc in re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M):
  if not 31<=int(f)<=120:continue
  pc=int(pc,16);j=bisect.bisect_right(keys,pc)-1
  if j<0:continue
  a=keys[j];n,fn=syms[a]
  if pc<a+n and fn.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):wanted[fn][pc-a]+=1
cnt=Counter();hot=Counter();pairs=Counter()
for u in range(47):
 group='opening-compact-loops' if u in (2,10,16,26,39) else 'opening-full-page'
 obj=root/group/f'recomp_{u:04}.c.o';cur=None
 proc=subprocess.Popen(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objdump','-d',obj],stdout=subprocess.PIPE,text=True)
 for line in proc.stdout:
  if line.endswith('>:\n'):
   m=re.match(r'^([0-9a-f]+) <(\w+)>:',line);cur=None
   if m and m[2] in wanted:fn=m[2];cur=wanted[fn];start=int(m[1],16)
   continue
  if not cur:continue
  m=re.match(r'^\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(\S+)\s*(.*)',line)
  if not m:continue
  n=cur.get(int(m[1],16)-start,0)
  if not n:continue
  op,args=m[2],m[3];k='non-stack'
  if op.startswith(('ld','st')) and re.search(r'\[(sp|x29)(?:\]|,)',args):
   operands=args.split('[')[0].strip(', ').split(', ')
   # Only the architectural register class is inferred; cannot prove spill or save.
   k='FP/SIMD' if all(re.fullmatch(r'[qdsbh]\d+',r) for r in operands) else 'callee-saved GPR' if all(re.fullmatch(r'x(19|2\d|30)',r) for r in operands) else 'other stack'
   hot[fn,k]+=n
   pairs[op,tuple(operands)]+=n
  cnt[k]+=n
 assert proc.wait()==0
assert sum(cnt.values())==sum(sum(c.values()) for c in wanted.values()),cnt
print(cnt);print(hot.most_common(15));print(pairs.most_common(12))
