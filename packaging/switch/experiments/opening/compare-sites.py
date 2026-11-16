"""Match sampled libc return addresses to relocations at exact offsets in the retained object."""
from pathlib import Path
import re,subprocess,bisect,collections
d=Path('build/switch-runtime/core-perf/opening-hot-profile')
sym={}
for line in (d/'symbols.txt').read_text().splitlines():
 a,n,_,name=line.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sym.get(a,(0,''))[0]:sym[a]=(n,name)
keys=sorted(sym)
asm=subprocess.check_output(['objdump','-dr',d/'host/threaded.cpp.o'],text=True)
sections={}
for key,body in re.findall(r'Disassembly of section (\S+):\n(.*?)(?=Disassembly of section |\Z)',asm,re.S):
 for start,name in re.findall(r'^([0-9a-f]+) <([^>]+)>:',body,re.M):
  sections[name]=(int(start,16),body)
for i in (1,2):
 s=(d/f'run-{i}.log').read_text();assert 'verified 120 original demo frames' in s
 pcs={(f,pc) for f,pc in re.findall(r'^\[FRAME_MODULE\] (\d+) (\w+) \w+ \S+/libc.so.6 __memcmpeq$',s,re.M)}
 hits=collections.Counter()
 for f,pc,lr in re.findall(r'^\[FRAME_LR\] (\d+) (\w+) (\w+)$',s,re.M):
  if int(f)<=30 or (f,pc) not in pcs:continue
  call=int(lr,16)-4;a=keys[bisect.bisect_right(keys,call)-1];n,name=sym[a]
  if call>=a+n or name not in sections:continue
  base,body=sections[name];off=call-a+base
  m=re.search(r'^\s*'+format(off,'x')+r': R_AARCH64_CALL26\s+(\S+)',body,re.M)
  if m:hits[(name,hex(call-a),m[1])]+=1
 print(i,*hits.most_common(),sep='\n')
