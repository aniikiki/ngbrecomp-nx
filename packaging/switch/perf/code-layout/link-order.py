"""Privately relink the exact 0.51 ARM game objects in the trained section order.

Do not replace the release package. Never move crt0, data or constructor tables.
"""
from pathlib import Path
import re,shlex,subprocess as sp,sys,gzip
order=Path(sys.argv[1]);dst=order.parent/'relayout';dst.mkdir(exist_ok=True)
sdk=Path('/opt/devkitpro');tools=sdk/'devkitA64/bin';base=Path('/work/build/switch-runtime')
b=base/'switch';regs=base/'native-regs'
commands=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=b,text=True).splitlines()
link=shlex.split(commands[-1].split('&&')[1])
for name in ('runtime.c','main.c'):
    cmd=next(shlex.split(l) for l in commands if l.endswith('/runtime/'+name))
    link[link.index(cmd[cmd.index('-o')+1])]=str(regs/(name+'.o'))
units=sorted(regs.glob('recomp_*.c.o'));assert len(units)==14
for obj in units:
    orig='CMakeFiles/ngb_boot_code.dir/work/build/switch-runtime/gen/'+obj.name.replace('.c.o','.o')
    link[link.index(orig)]=str(obj)
link[1:1]=[str(regs/(name+'.o')) for name in ('entry','gates','checkpoint','backend-clip')]
known=set(order.read_text().splitlines());sections={}
for v in link:
    if not v.endswith('.o'):continue
    path=b/v
    if path.name not in ('entry.o','gates.o','checkpoint.o') and not path.name.startswith('recomp_'):continue
    tab=sp.check_output([tools/'aarch64-none-elf-objdump','-t',path],text=True)
    for l in tab.splitlines():
        fields=l.split()
        if len(fields)<6 or fields[-1] not in known or fields[-4]!='F':continue
        name=fields[-1];section=fields[-3]
        if not section.startswith('.text.'):continue
        sections[name]=f'*{path.name}({section})'
rules=[sections[n] for n in order.read_text().splitlines() if n in sections]
assert len(rules)>30 and len(set(rules))==len(rules)
script=(sdk/'libnx/switch.ld').read_text();tag='\t\tKEEP (*(.crt0))'
assert script.count(tag)==1
(dst/'switch.ld').write_text(script.replace(tag,tag+'\n'+'\n'.join('        '+r for r in rules)))
spec=(sdk/'libnx/switch.specs').read_text()
tag='%:getenv(DEVKITPRO /libnx/switch.ld)';assert spec.count(tag)==1
(dst/'switch.specs').write_text(spec.replace(tag,str(dst/'switch.ld')))
link[link.index('-specs=/opt/devkitpro/libnx/switch.specs')]='-specs='+str(dst/'switch.specs')
link.insert(1,'-Wl,--strip-debug')
elf=dst/'guest.elf';link[link.index('-o')+1]=str(elf)
sp.run(link,cwd=b,check=True)
nm=sp.check_output([tools/'aarch64-none-elf-nm','-n','-S',elf])
(dst/'symbols.gz').write_bytes(gzip.compress(nm,mtime=0))
addrs={s[3]:int(s[0],16) for row in nm.decode().splitlines() if len(s:=row.split())==4 and s[3] in sections}
selected=[addrs[n] for n in order.read_text().splitlines() if n in sections]
assert selected==sorted(selected) and len(set(selected))==len(rules)
print('Real Switch ELF verified:',len(rules),'reordered whole functions;',len(known)-len(rules),'non-separable sections left at linker defaults')
