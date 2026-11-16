"""Compile ABI metadata from the actual Horizon backend, then decode the opening seed with it."""
from pathlib import Path
from collections import Counter
import shlex, struct, subprocess as sp, tempfile
base=Path('/work/build/switch-runtime')
build=base/'switch'
cmd=next(shlex.split(l) for l in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=build,text=True).splitlines() if l.endswith('/vk/backend.cpp'))
src=Path(cmd[-1]);s=src.read_text()
fields=('vs','ps','fill','has_rt','has_ds','ds_format','samples')
expr=['sizeof(PipeKey)','sizeof(FixedKey)','sizeof(PixelKey)']+[f'__builtin_offsetof(PipeKey,{f})' for f in fields]
anchor='struct PipeHash {'
assert s.count(anchor)==1
s=s.replace(anchor,'__attribute__((used,section(".recipe_layout"))) const uint32_t layout[]={'+','.join(expr)+'};\n'+anchor)
with tempfile.TemporaryDirectory() as tmp:
    t=Path(tmp);probe=t/'backend.cpp';probe.write_text(s);cmd[-1]=str(probe)
    cmd[1:1]=['-I'+str(src.parent)]
    cmd[cmd.index('-o')+1]=str(t/'backend.o')
    if '-MF' in cmd: cmd[cmd.index('-MF')+1]=str(t/'backend.d')
    sp.run(cmd,cwd=build,check=True)
    sp.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objcopy','-O','binary','-j','.recipe_layout',t/'backend.o',t/'layout'],check=True)
    pk,fk,psk,*offsets=struct.unpack('<10I',(t/'layout').read_bytes())
record=(base/'core-perf/opening-present-combined/opening-120.recipes').read_bytes()
assert record[:8]==b'NGBD3DC1'
i=8;modules={};pipes=set();configs=Counter()
while i<len(record):
    kind,key,n=struct.unpack_from('<cQI',record,i);i+=13
    data=record[i:i+n];i+=n;assert len(data)==n
    if kind==b'K':
        assert n==pk and data not in pipes
        pipes.add(data)
        config=tuple(struct.unpack_from('<I',data,o)[0] for o in offsets[2:])
        configs[config]+=1
    else:
        assert kind in (b'V',b'F',b'P') and key not in modules
        if kind==b'F': assert n==11+fk
        if kind==b'P': assert n==psk
        if kind==b'V': assert n==15+4*struct.unpack_from('<I',data,11)[0]
        modules[key]=kind
for data in pipes:
    v,p=[struct.unpack_from('<Q',data,o)[0] for o in offsets[:2]]
    assert modules[v] in (b'V',b'F') and modules[p]==b'P'
assert (len(pipes),len(modules))==(167,118)
print('Horizon sizes',pk,fk,psk,'offsets',offsets,'verified',len(pipes),len(modules))
print('fill, color, depth flags, stored depth format, samples -> pipeline count:',sorted(configs.items()))
