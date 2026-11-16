"""Compile a journal worker without instrumenting reads. GCC's TSAN pass
still identifies writes; remove only calls to known empty read observers
in the emitted ARM assembly. Retain all read-write and write range hooks."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
# Use the raw journal, since grouping at every private poll also costs cycles.
s=(here/'journal-build.py').read_text();i=s.index("exec(compile(s,'worker-journal'")
s=s[:i]+'''s=s.replace("d=p/'opt050/actor-journal'","d=p/'opt050/actor-store-only'")
tag="sp.run(cmd,cwd=w,check=True)"
new="""asm=d/'store-only.s';cmd[cmd.index('-c')]='-S';cmd[cmd.index('-o')+1]=str(asm);sp.run(cmd,cwd=w,check=True)
original=asm.read_text()
# Out-of-line read observers return void, and preserve only the normal ABI.
clean,count=re.subn(r'(?m)^\\\\s*bl\\\\s+__tsan_(?:unaligned_)?read(?:1|2|4|8|16|_range)(?:\\\\.localalias)?\\\\s*$', '', original)
print('discarded empty read observer calls',count,flush=True)
asm.write_text(clean);sp.run([cmd[0],'-c',str(asm),'-o',o],cwd=w,check=True)"""
s=s.replace(tag,new)
'''+s[i:]
exec(compile(s,'store-only-worker','exec'))
