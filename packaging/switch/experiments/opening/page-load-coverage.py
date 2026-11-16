"""Which sampled page lookups could the five-unit MEM32 experiment reach?
Identify only a simple, straight-line, data-linked lookup->RAM operation.
A word instruction is a necessary condition, not proof the macro was MEM32.
"""
from pathlib import Path
from collections import Counter,defaultdict
import contextlib,io,re,runpy,subprocess,shutil
p=Path(__file__).parent
with contextlib.redirect_stdout(io.StringIO()):
 q=runpy.run_path(str(p/'translation-pc-budget.py'))
wanted=defaultdict(Counter)
for (fn,o),_ in q['samples']:
 if q['tags'][fn].get(o//4)=='page table load':wanted[fn][o]+=1
objdump=shutil.which('llvm-objdump') or subprocess.check_output(['xcrun','-f','llvm-objdump'],text=True).strip()
c=Counter()
def operand(load,lines):
 # Decode only the fall-through fast arm with this exact address calculation.
 if len(lines)<5 or lines[0][0]!='cmp' or lines[1][0] not in ('b.hs','b.ls'):return 'unresolved'
 bound=load[1].split(',')[0];cmp=lines[0][1].split(', ')
 if len(cmp)!=2:return 'unresolved'
 if lines[1][0]=='b.hs' and cmp[1]==bound:va=cmp[0]
 elif lines[1][0]=='b.ls' and cmp[0]==bound:va=cmp[1]
 else:return 'unresolved'
 if lines[2][1].split(', ')[1:]!=['x'+va[1:],'#0x7fffffff']:return 'unresolved'
 if lines[2][0]!='and' or lines[3][0]!='add':return 'unresolved'
 m=re.fullmatch(r'(x\d+), x26, (x\d+)',lines[3][1])
 if not m or lines[2][1].split(', ')[0]!=m[2]:return 'unresolved'
 r=m[1]
 for op,args in lines[4:]:
  if re.fullmatch(r'[^,]+, \['+r+r'\]',args):
   if op in ('ldr','str') and re.match('[ws][0-9]',args):return 'word'
   if op in ('ldrb','strb','ldrh','strh','ldrsb','ldrsh'):return 'byte/half'
   return 'unresolved'
  # Only pass single-register non-memory writes that cannot clobber the base.
  if op not in ('mov','add','sub','and','lsr','lsl') or args.split(',')[0] in (r,'w'+r[1:]):break
 return 'unresolved'
for u in range(47):
 hot=u in (2,10,16,26,39)
 obj=q['q']['root']/('opening-compact-loops' if hot else 'opening-full-page')/f'recomp_{u:04}.c.o'
 data=subprocess.check_output([objdump,'-d','--no-show-raw-insn',str(obj)],text=True)
 parts=re.split(r'(?m)^([0-9a-f]+) <([^>]+)>:\n',data)
 for start,fn,body in zip(parts[1::3],parts[2::3],parts[3::3]):
  if fn.endswith('.localalias'):fn='ngb_reg_'+fn.removesuffix('.localalias')
  if fn not in wanted:continue
  ops={int(a,16)-int(start,16):(op,args.split('//')[0].strip()) for a,op,args in re.findall(r'(?m)^\s*([0-9a-f]+):[ \t]+(\S+)[ \t]*([^\n]*)$',body)}
  for off,n in wanted[fn].items():
   assert ops[off][0]=='ldr' and '[x27,' in ops[off][1],(u,fn,hex(off),ops[off])
   c['inside five' if hot else 'outside five',operand(ops[off],[ops[i] for i in range(off+4,off+44,4) if i in ops])]+=n
assert sum(c.values())==144,c
for k,v in sorted(c.items()):print(*k,v)
