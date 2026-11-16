"""Link the private ABI as a separate Switch program; leave the baseline alone."""
import argparse
import gzip
import hashlib
from pathlib import Path
import shlex
import struct
import subprocess as sp

sdk = Path('/opt/devkitpro')
base = Path('/work/build/switch-runtime')
regular = base/'switch'
work = base/'native-regs'
runtime = Path('/work/packaging/switch/runtime')
opts = argparse.ArgumentParser()
opts.add_argument('--rigid-clip',action='store_true')
clip = opts.parse_args().rigid_clip
version = '0.51.0-rc1' if clip else '0.50.0-rc1'
out = base/'history'/version
out.mkdir(parents=True, exist_ok=True)
commands = sp.check_output(['ninja', '-t', 'commands', 'ngb-startup'], cwd=regular, text=True).splitlines()
# Keep the original linker script, SDK, libraries and their ordering.
link = shlex.split(commands[-1].split('&&')[1])
if clip:
    cc = next(shlex.split(l) for l in commands if l.endswith('/vk/backend.cpp'))
    obj = str(work/'backend-clip.o')
    cc[cc.index('-o')+1]=obj
    cc[cc.index('-MF')+1]=obj+'.d'
    cc.insert(1,'-DNGB_RIGID_CLIP')
    sp.run(cc,cwd=regular,check=True)
    link.insert(1,obj) # selected in place of the backend in the static archive
for name in ('runtime.c', 'main.c'):
    cmd = next(shlex.split(l) for l in commands if l.endswith(str(runtime/name)))
    ix = cmd.index('-o') + 1
    obj = work/(name+'.o')
    link[link.index(cmd[ix])] = str(obj)
    cmd[ix] = str(obj)
    cmd[cmd.index('-MF')+1] = str(obj)+'.d'
    cmd.insert(1, '-DNGB_REGISTER_PACKAGE')
    if clip: cmd.insert(1,'-DNGB_RIGID_CLIP')
    sp.run(cmd, cwd=regular, check=True)
objects = sorted(work.glob('recomp_*.c.o'))
assert len(objects) == 14
for obj in objects:
    orig = 'CMakeFiles/ngb_boot_code.dir/work/build/switch-runtime/gen/'+obj.name.replace('.c.o','.o')
    link[link.index(orig)] = str(obj)
cp = work/'checkpoint.o'
cc = sdk/'devkitA64/bin/aarch64-none-elf-gcc'
sp.run([cc,'-c',Path(__file__).with_name('checkpoint.S'),'-o',cp],check=True)
link[1:1] = [str(work/'entry.o'), str(work/'gates.o'), str(cp)]
elf = work/'ngb-startup.elf'
link[link.index('-o')+1] = str(elf)
sp.run(link, cwd=regular, check=True)
nm = sp.check_output([sdk/'devkitA64/bin/aarch64-none-elf-nm','-n','-S',elf])
for sym in [b'ngb_reg_checkpoint', b'ngb_reg_sub_00018A60', b'ngb_gate_indirect', b'ngb_reg_entries']:
    assert b' '+sym+b'\n' in nm, sym
(work/'symbols.gz').write_bytes(gzip.compress(nm,mtime=0))
nacp = work/'ngb-startup.nacp'
nro = work/'ngb-startup.nro'
sp.run([sdk/'tools/bin/nacptool','--create','NGB Startup','NGB port development',version,nacp],check=True)
sp.run([sdk/'tools/bin/elf2nro',elf,nro,'--nacp='+str(nacp),'--icon='+str(sdk/'libnx/default_icon.jpg'),'--romfsdir='+str(base/'romfs')], check=True)
def asset(path,i):
    with path.open('rb') as f:
        f.seek(0x10)
        assert f.read(4) == b'NRO0'
        f.seek(0x18)
        start = int.from_bytes(f.read(4),'little')
        f.seek(start)
        assert f.read(4) == b'ASET'
        f.seek(start+8+16*i)
        offset,size = struct.unpack('<QQ', f.read(16))
        assert size and start+offset+size <= path.stat().st_size
        f.seek(start+offset)
        h=hashlib.sha256()
        while size:
            block=f.read(min(size,1024*1024))
            assert block
            h.update(block)
            size-=len(block)
        return h.digest()
assert asset(nro,1)==hashlib.sha256(nacp.read_bytes()).digest()
assert asset(nro,2)==asset(regular/'ngb-startup.nro',2)
assert nacp.read_bytes()[0x3060:0x3070].split(b'\0')[0]==version.encode()
for f in (work/'symbols.gz',nro):
    f.replace(out/f.name)
print('Verified NRO, NACP version and unchanged RomFS:',out,flush=True)
