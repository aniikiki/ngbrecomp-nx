"""Compile all 47 guest units as one register ABI domain. An address taken in a
table must still point at the public ABI. Preserve local calls and original
poll/callback sites. Only named private direct branches bypass the gates."""
import os,re
from pathlib import Path
root=Path('/work');abi=root/'packaging/switch/arm-registers'
d=root/'build/switch-runtime/core-perf/opening-full-guest';d.mkdir(exist_ok=True)
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text();s,n=re.subn(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))',s,flags=re.M);assert n==1
# Unit 30 also owns the non-hex XBE startup symbol. It needs the same
# public-to-private entry wrapper for host boot as the numeric game routines.
numeric=r'(?:sub_|d3d_orig_)[0-9A-F]+'
assert s.count(numeric)==2
s=s.replace(numeric,'(?:'+numeric+'|xbe_entry_point)')
# Avoid carrying temporary assembly for three copies of the whole guest
# after gates.py has built the actual object.
exec(compile(s,'full-guest','exec'),{})
exec(compile((abi/'gates.py').read_text(),'full-gates','exec'),{})
assert len(list(d.glob('recomp_*.c.o')))==47
for f in d.glob('recomp_*.s'):f.unlink()
