"""Measure same-base scalar groups in straight-line generated code, preserving every actual access."""
from pathlib import Path
import re
REG=r'(?:eax|ebx|ecx|edx|esi|edi|ebp|esp)'
mem=re.compile(r'\b(S?MEM(?:8|16|32)|MEMF)\(('+REG+r')(?: ([+-]) (0x[\da-fA-F]+|\d+))?\)')
barrier=re.compile(r'\b(?:if|goto|return|switch|volatile|asm)\b|[{}:]|\b(?:ngb_|RECOMP_|PUSH|POP|CALL)')
# Accept only explicit arithmetic/assignments and known scalar constructors.
call=re.compile(r'\b(\w+)\s*\(')
allow={'XMM_SCALAR','LO8','LO16','ZX8','ZX16','int32_t','uint32_t','int16_t','uint16_t','int8_t','uint8_t'}
def transform(s,fast=False):
 out=[];group=[];base=None;ops=[]
 def flush():
  nonlocal group,base,ops
  if len(ops)>=2:
   lo=min(o for o,n in ops);hi=max(o+n for o,n in ops)
   if hi-lo<=128:
    if not fast:
     out.append(f'    if(ms_on)ms_group({base}+({lo}),{hi-lo}u,{len(ops)}u);\n')
    elif len(ops)>=4 and len(set(ops))>=3 and all('=' in l and not re.match(r'\s*(?:const|unsigned|int|float|double|uint|struct|static)',l) for l in group):
     def replace(m):
      o=int(m[4] or '0',0)*(-1 if m[3]=='-' else 1)
      typ={'MEMF':'float','MEM32':'uint32_t','SMEM32':'int32_t','MEM16':'uint16_t','SMEM16':'int16_t','MEM8':'uint8_t','SMEM8':'int8_t'}[m[1]]
      return f'(*(volatile {typ} *)(ms_p+{o-lo}))'
     out.append(f'    {{uint32_t ms_va={base}+({lo}); if(__builtin_expect((ms_va&4095u)+{hi-lo}u<=ngb_fast_page_bytes[ms_va>>12],1)){{unsigned char *ms_p=ngb_fast_ram+(ms_va&0x7fffffffu);\n')
     out.extend(mem.sub(replace,l) for l in group);out.append('    }else{\n');out.extend(group);out.append('    }}\n')
     group=[];base=None;ops=[];return
  out.extend(group);group=[];base=None;ops=[]
 for line in s.splitlines(True):
  x=line.split('/*')[0].strip()
  matches=list(mem.finditer(x));clean=mem.sub('ms_operand',x)
  if (not x.endswith(';') or barrier.search(x) or 'MEM' in clean or set(call.findall(clean))-allow or
      len(set(m[2] for m in matches))>1):
   flush();out.append(line);continue
  b=matches[0][2] if matches else base
  if len(group)>=16 or base!=b:flush()
  if not b or re.search(r'\b'+b+r'\s*(?:=(?!=)|\+\+|--|[+\-*/&|^]=)',clean):
   flush();out.append(line);continue
  base=b;group.append(line)
  for m in matches:
   off=int(m[4] or '0',0)*(-1 if m[3]=='-' else 1)
   n={'8':1,'16':2,'32':4,'F':4}[m[1].split('MEM')[1]];ops.append((off,n))
 flush()
 return 'extern unsigned ms_on;extern void ms_group(unsigned,unsigned,unsigned);\n'+''.join(out)

if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-mixed-span'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_%04d.c'%u for u in (2,10,16,26,39)]"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'mixed-span','exec'),{'transform':transform})
    for f in Path('build/switch-runtime/core-perf/opening-mixed-span').glob('recomp_*.c'):f.unlink()
