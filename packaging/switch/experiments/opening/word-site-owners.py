"""Attribute the measured late word accesses to their generated instruction (GCC macro expansion)."""
import sys, collections, re, runpy, shlex, subprocess, tempfile
from pathlib import Path
p=Path(__file__).resolve().parent
base=Path('/work/build/switch-runtime')
w=base/'switch'
d=base/'core-perf/opening-word-site-census'
obs=runpy.run_path(str(p/'word-site-census.py'))
weights={(int(u),int(i)):int(l) for u,i,n,pg,v,l,h in re.findall(r'^\[WS_SITE\] (\d+) (\d+) (\d+) (\w+) (\d+) (\d+) (\d+)$',(d/'budget.log').read_text(),re.M)}
commands=subprocess.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines()
owners=collections.Counter();ops=collections.Counter();kinds=collections.Counter();matched=set()
nodes=collections.Counter()
def node_lines(lines):
 result={}
 for i,line in enumerate(lines):
  header=re.fullmatch(r'(loc_[0-9A-F]+): ; ngb_guest_block_poll\(\);',line)
  if not header or i+10>=len(lines):continue
  cmp=re.search(r'_fa = \(uint32_t\)\(MEM32\((\w+) \+ 0xC\)\)',lines[i+1])
  if not cmp or 'if (CMP_' not in lines[i+3] or lines[i+4].strip() or not re.fullmatch(r'loc_[0-9A-F]+: ;',lines[i+5]):continue
  reg=cmp[1]
  if lines[i+6].strip()!=f'{reg} = MEM32({reg} + 4);':continue
  if f'cmp {reg}, 0 (32-bit)' not in lines[i+8] or f'if (CMP_NE(_fa, _fb)) goto {header[1]};' not in lines[i+9]:continue
  result[i+2]=(header[1],'compare')
  result[i+7]=(header[1],'advance')
 return result
for ix,u in enumerate(obs['units']):
 n=f'recomp_{u:04}.c';cmd=next(shlex.split(l) for l in commands if l.endswith('/'+n))
 with tempfile.TemporaryDirectory() as t:
  src=Path(t)/n;src.write_text(obs['transform']((base/'gen'/n).read_text(),u));lines=src.read_text().splitlines()
  selected=node_lines(lines) if "--nodes" in sys.argv else {}
  # Same headers and predefined macros used by the counter build; keep line markers.
  flags=[a for a in cmd[1:] if a.startswith(('-I','-D','-m','-std='))]
  out=subprocess.check_output([cmd[0],'-E','-O3','-I'+str(d),'-include',str(d/'regs.h'),'-I'+str(base/'gen'),*flags,str(src)],cwd=w,text=True)
  local=False;owner=None
  for line in out.splitlines():
   marker=re.match(r'^# (\d+) "([^"]+)"',line)
   if marker:
    pos=int(marker[1]);local=marker[2]==str(src);continue
   if local:
    f=re.match(r'void (\w+)\(void\)$',line)
    if f:owner=f[1]
    # Capture calls, including nested macros, by their final constant argument.
    for s in re.findall(r'ws_addr\(\(uint32_t\).*?,\s*(\d+)\)',line):
     key=(ix,int(s))
     if key not in weights:continue
     assert key not in matched and owner and pos<=len(lines),(key,pos)
     matched.add(key);count=weights[key];raw=lines[pos-1].strip()
     if pos in selected:nodes[(u,owner,*selected[pos])]+=count
     owners[owner]+=count;ops[(owner,raw)]+=count
     kind=next((k for k in ('PUSH32','POP32','MEM32') if k in raw),'other macro')
     kinds[kind]+=count
   pos+=1
assert matched==set(weights),(len(matched),len(weights),list(set(weights)-matched)[:10])
for c in (kinds,owners,ops):
 for k,v in c.most_common(12):print(round(v/90,1),str(k)[:170])
 print()
if "--nodes" in sys.argv:
 for kind in ("compare","advance"):
  hits=sum(v for k,v in nodes.items() if k[-1]==kind)
  print(kind,hits,"per late frame",hits/90,"fraction of measured words",hits/sum(weights.values()))
 print("hottest node sites",nodes.most_common(12))
