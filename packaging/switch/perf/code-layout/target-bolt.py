"""Diagnostic only: make a profile-compatible AArch64 container for post-link analysis.
An ordinary nonzero text address avoids BOLT confusing Horizon's zero-address code
with undefined symbols. The result is deliberately NOT a bootable Switch NRO."""
from pathlib import Path
import sys
p=Path('/work/build/switch-runtime');d=p/'opt050/bolt'
s=Path('/work/packaging/switch/perf/code-layout/link-order.py').read_text()
s=s.replace("order=Path(sys.argv[1]);dst=order.parent/'relayout';dst.mkdir(exist_ok=True)","")
s=s[:s.index('known=set')]+'''
script=(sdk/'libnx/switch.ld').read_text().replace('__start__ = 0x0','__start__ = 0x400000')
j=script.index('SECTIONS');brace=script.index('{',j)
# Replace the initial location assignment, do not create a text file padded by 4MB.
import re
tail=script[brace+1:];tail,n=re.subn(r'(?m)^\s*\.\s*=\s*0\s*;', '\\n    . = 0x400000;',tail,count=1)
if not n:tail='\\n    . = 0x400000;'+tail
(d/'analysis.ld').write_text(script[:brace+1]+tail)
spec=(sdk/'libnx/switch.specs').read_text().replace('%:getenv(DEVKITPRO /libnx/switch.ld)',str(d/'analysis.ld'))
(d/'analysis.specs').write_text(spec)
link[link.index('-specs=/opt/devkitpro/libnx/switch.specs')]='-specs='+str(d/'analysis.specs')
link.insert(1,'-Wl,--emit-relocs,--strip-debug,-z,nopack-relative-relocs')
elf=d/'analysis.elf';link[link.index('-o')+1]=str(elf);sp.run(link,cwd=b,check=True)
'''
exec(compile(s,'target-bolt-link','exec'))
