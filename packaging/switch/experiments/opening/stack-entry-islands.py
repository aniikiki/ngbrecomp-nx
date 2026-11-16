"""Screen only entry-dominated stack accesses separated by pure register arithmetic.
Use archived late entry visits, never infer loop iterations from function counts."""
from pathlib import Path
import ast,collections,re
b=Path('build/switch-runtime');d=b/'core-perf'
names={n.removeprefix('ngb_reg_') for n,_ in ast.literal_eval((d/'opening-split-profile/page-provenance.txt').read_text().split('esp by guest function ')[1])}
assert len(names)==44
cnt=collections.Counter()
s=(d/'opening-setup/entry-mix.log').read_text()
fs=set()
for f,line in re.findall(r'^\[ENTRY_MIX\] (\d+) (.*)$',s,re.M):
 if 31<=int(f)<=120:
  assert int(f) not in fs;fs.add(int(f))
  for a,v in re.findall(r'([0-9a-f]+):(\d+)',line):cnt[int(a,16)]+=int(v)
assert fs==set(range(31,121))
reg=r'(?:eax|ebx|ecx|edx|esi|edi|ebp)'
stack=re.compile(r'(?:PUSH32\(esp, '+reg+r'\)|POP32\(esp, '+reg+r'\)|'+reg+r' = MEM32\(esp(?: [+-] (?:0x[\dA-Fa-f]+|\d+))?\));')
safe=set('eax ebx ecx edx esi edi ebp _fa _fb _fas _fbs uint32_t int32_t'.split())
rows=[];seen=set()
for p in sorted((b/'gen').glob('recomp_*.c')):
 src=re.sub(r'#ifdef NGB_DIRECT3D\n(void d3d_orig_\w+\(void\))\n#else\nvoid sub_\w+\(void\)\n#endif',r'\1',p.read_text())
 for m in re.finditer(r'^void (\w+)\(void\)\n\{(.*?)^\}',src,re.M|re.S):
  n,body=m.groups()
  if n not in names:continue
  seen.add(n)
  prel,sep,body=body.partition('loc_'+n.split('_')[-1]+': ;')
  if not sep or re.search(r'\bgoto\b|\breturn\s*;',re.sub(r'/\*.*?\*/','',prel,flags=re.S)):continue
  groups=[];run=0
  for line in re.sub(r'/\*.*?\*/','',body,flags=re.S).splitlines():
   line=line.strip()
   if not line:continue
   if stack.fullmatch(line):run+=1;continue
   if run:groups.append(run);run=0
   # No memory, unknown macros, calls, ESP changes or control transfers.
   t=re.sub(r'0x[0-9a-fA-F]+[uU]?|\b\d+[uU]?','0',line)
   parts=t.split(';'); assert parts
   if parts[-1].strip() or not all(re.fullmatch(r'(?:'+reg+r'|_fa|_fb|_fas|_fbs)\s*=\s*[\w\s()+&|^<>~*-]+',v.strip()) for v in parts[:-1]) or set(re.findall(r'[A-Za-z_]\w*',t))-safe:break
  if run:groups.append(run)
  if len(groups)>=2:
   visits=cnt[int(n.split('_')[-1],16)]
   rows.append(((len(groups)-1)*visits,visits,n,groups))
assert seen==names
print('functions checked',len(seen),'eligible',len(rows),'extra checks removable vs adjacent grouping per frame (entry-only, older replay counts):',sum(x[0] for x in rows)/90)
for r in sorted(rows,reverse=True):print(*r)
