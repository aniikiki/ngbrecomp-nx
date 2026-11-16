"""Group ESP/EBP-relative 32-bit loads and stores across pure register work.
No calls, branches, register-base assignments or other memory operands inside
a span. A failed guard executes the unchanged block, including fault order."""
import re,sys,os
from pathlib import Path
units=(2,16,26,39)
R=r'(?:eax|ebx|ecx|edx|esi|edi|esp|ebp)'
alu=re.compile(r'('+R+r') = ('+R+r'|0x[\dA-Fa-f]+u?|\d+)(?: (?:\+|-|\^|\||&) ('+R+r'|0x[\dA-Fa-f]+u?|\d+))?;')
op=re.compile(r'(?:('+R+r') = MEM32\((esp|ebp)(?: ([+-]) (0x[\da-fA-F]+|\d+))?\)|MEM32\((esp|ebp)(?: ([+-]) (0x[\da-fA-F]+|\d+))?\) = ('+R+r'|0x[\da-fA-F]+u?|\d+));')
def transform(s,collect):
 lines=s.splitlines(True);out=[];pending=[];base=None
 def flush():
  nonlocal base
  mem=[i for i,(l,m) in enumerate(pending) if m is not None]
  if len(mem)<2:out.extend(l for l,m in pending)
  else:
   z=mem[-1]+1;seq=pending[:z];offs=[int(m[4] or m[7] or '0',0)*(-1 if (m[3] or m[6])=='-' else 1) for _,m in seq if m]
   lo=min(offs);n=max(offs)+4-lo
   raw=''.join(l for l,m in seq)
   if n>256 or any(x%4 for x in offs):out.append(raw)
   else:
    alt=[];oi=iter(offs)
    for l,m in seq:
     if m:
      x=next(oi)-lo;t='q['+str(x//4)+']'
      l='    '+(m[1]+' = '+t if m[1] else t+' = '+m[8])+';\n'
     alt.append(l)
    # Integer VA wrap is defined. A single admitted page cannot wrap mid-span.
    new=f'    {{ uint32_t va={base}+({lo}); if (!(va&3u) && (va&4095u)+{n}u<=ngb_fast_page_bytes[va>>12]) {{ volatile uint32_t *q=(volatile uint32_t *)(ngb_fast_ram+(va&0x7fffffffu));\n'+''.join(alt)+'    } else {\n'+raw+'    } }\n'
    if '--audit' in sys.argv:
     new=new.replace('volatile uint32_t *q=',f'extern unsigned span_on;extern uint64_t span_count[2];if(span_on){{span_count[0]++;span_count[1]+={len(mem)};}} volatile uint32_t *q=')
    collect(raw,new,base,len(mem));out.append(new)
   out.extend(l for l,m in pending[z:])
  pending.clear();base=None
 for l in lines:
  x=l.strip();m=op.fullmatch(x)
  if m:
   b=m[2] or m[5]
   if b!=base or m[1]==b:flush()
   if m[1]!=b:
    base=b;pending.append((l,m));continue
  elif pending:
   a=alu.fullmatch(x)
   if a and a[1]!=base and len(pending)<16:pending.append((l,None));continue
  flush();out.append(l)
 flush();return ''.join(out)
if __name__=='__main__':
 import collections
 root=Path.cwd();gen=root/'build/switch-runtime/gen';stats=collections.Counter();blocks={}
 d=gen.parent/'core-perf'/('opening-span-audit' if '--audit' in sys.argv else 'opening-frame-spans');build='--build' in sys.argv
 def got(raw,alt,b,n):stats[b]+=1;stats['checked_ops']+=n;blocks[raw]=alt
 if build:d.mkdir(exist_ok=True)
 for u in units:
  name=f'recomp_{u:04}.c';s=transform((gen/name).read_text(),got)
  if build:(d/name).write_text(s)
 print('groups and word accesses',dict(stats),'distinct',len(blocks),flush=True)
 if '--check' in sys.argv:
  import tempfile,subprocess as sp
  # Use actual sequences; keep both address registers initially within RAM.
  t=Path(__file__).with_name('stack-groups-check.inc').read_text().replace('initial.r[4]=8192+side*4;', 'initial.r[4]=initial.r[5]=8192+side*4;')
  for name,which in [('reference',0),('candidate',1)]:
   t+='\nstatic void '+name+'(unsigned n){switch(n){\n'
   for i,pair in enumerate(blocks.items()):t+=f'case {i}:{{'+pair[which]+'}break;\n'
   t+='default:abort();}}\n'
  with tempfile.TemporaryDirectory() as tmp:
   f=Path(tmp)/'check.c';f.write_text(t+f'int main(void){{return check({len(blocks)});}}');e=f.with_suffix('')
   sp.run(['cc','-O0','-fno-strict-aliasing',f,'-o',e],check=True);sp.run([e],check=True)
 if build:
  abi=root/'packaging/switch/arm-registers';os.environ['NGB_REG_OUT']=str(d)
  s=(abi/'compile.py').read_text()
  s=re.sub(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))',s,flags=re.M)
  num=r'(?:sub_|d3d_orig_)[0-9A-F]+'
  s=s.replace(num,'(?:'+num+'|xbe_entry_point)')
  s=s[:s.index("f=o/'entry.S'")].replace('ex.map(build,units)','ex.map(build,'+repr([f'recomp_{i:04}.c' for i in units])+')')
  k=' sp.run(c,cwd=w,check=True)';assert s.count(k)==1
  exec(compile(s.replace(k,' c[-1]=str(o/n)\n'+k),'frame-spans','exec'),{})
  exec(compile((abi/'gates.py').read_text(),'span-gates','exec'),{})
  for pat in ('recomp_*.s','recomp_*.c'):
   for f in d.glob(pat):f.unlink()
