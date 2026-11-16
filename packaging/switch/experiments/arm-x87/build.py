"""Compile the packaged fourteen ARM units with a different x87 lowering.
The copied generated files never change production input or its cached ABI."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent;root=Path('/work');base=root/'build/switch-runtime'
mode=sys.argv[1];assert mode in ('integer','fcvt')
d=base/('opt050/x87-'+mode);d.mkdir(exist_ok=True)
g=base/'gen'
for name in ('recomp_types.h','recomp_funcs.h','recomp_regs.h'):
 s=(g/name).read_text()
 if name=='recomp_types.h':
  beg=s.index('static inline double recomp_fp_round24(');end=s.index('#define RECOMP_FP_PC',beg)
  fast=(here/'round.inc').read_text()
  if mode=='fcvt':
   tag='    if (__builtin_expect(exp && exp!=2047u,1))'
   fast=fast.replace(tag,'    if (__builtin_expect(exp-897u < 253u,1)) return (double)(float)x;\n'+tag)
  s=s[:beg]+s[beg:end].replace('round24(', 'round24_reference(')+fast+s[end:]
  a=s.index('        double lo=floor(value), fraction=value-lo;');b=s.index('        break;',a)
  s=s[:a]+'''        __asm__("frintn %d0,%d1" : "=w"(rounded) : "w"(value));
'''+s[b:]
 (d/name).write_text(s)
abi=root/'packaging/switch/arm-registers';s=(abi/'compile.py').read_text().replace("o=w.parent/'native-regs'",'o=Path('+repr(str(d))+')')
# Quoted includes in the source resolve first against its own directory.
s=s.replace(' sp.run(c,cwd=w,check=True)', " src=Path(c[-1]);(o/n).write_bytes(src.read_bytes());c[-1]=str(o/n)\n sp.run(c,cwd=w,check=True)",1)
exec(compile(s,'x87-cross','exec'),{'__name__':'__main__'})
s=(abi/'gates.py').read_text().replace('/switch-runtime/native-regs','/switch-runtime/opt050/x87-'+mode)
exec(compile(s,'x87-gates','exec'),{'__name__':'__main__'})
