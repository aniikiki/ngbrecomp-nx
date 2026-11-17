"""Exercise a published ARM basic-block path and the original Xbox path; no game boot."""
from pathlib import Path
import hashlib, struct
from unicorn import Uc, UC_ARCH_X86, UC_ARCH_ARM64, UC_MODE_32, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESI
from unicorn.arm64_const import UC_ARM64_REG_X19, UC_ARM64_REG_X24, UC_ARM64_REG_X26, UC_ARM64_REG_X27, UC_ARM64_REG_X22
n=Path('build/switch-runtime/history/0.56.23/ngb-startup.nro').read_bytes()
assert hashlib.sha256(n).hexdigest()=='5a7c86da8d46742e213c84c11ef1a488466682e422e695f2cbe42a80824bb60b'
b=Path('game_files/default.xbe').read_bytes()
u=lambda i:struct.unpack_from('<I',b,i)[0]
base=0x1e0000
for i in range(u(0x11c)):
    va,_,off,size=struct.unpack_from('<4I',b,u(0x120)-u(0x104)+56*i+4)
    if va<=base and base+4096<=va+size:break
else:raise ValueError('XBE section missing')
def run(cpu,start,stops):
    seen=[]
    def hook(cpu,pc,size,data):
        if pc in stops:
            seen.append(pc);cpu.emu_stop()
    cpu.hook_add(UC_HOOK_CODE,hook)
    cpu.emu_start(start,0,count=100)
    assert len(seen)==1
    return seen[0]
for eax,esi in ((0,0),(1,2),(0xffffffff,0xffffffff),(0x80000000,0)):
    x=Uc(UC_ARCH_X86,UC_MODE_32);x.mem_map(base,4096);x.mem_write(base,b[off+base-va:off+base-va+4096])
    x.reg_write(UC_X86_REG_EAX,eax);x.reg_write(UC_X86_REG_ESI,esi)
    assert run(x,0x1e0175,{0x1e0181,0x1e018b})==0x1e018b
    a=Uc(UC_ARCH_ARM64,UC_MODE_ARM);page=0x1e1c000
    a.mem_map(page,4096);a.mem_write(page,n[page:page+4096])
    a.mem_map(0x10002000,4096);a.mem_map(0x20000000,4096)
    a.mem_write(0x20000008,struct.pack('<I',0x3000))
    for reg,v in ((UC_ARM64_REG_X19,eax),(UC_ARM64_REG_X24,esi),(UC_ARM64_REG_X22,0x2080),
                  (UC_ARM64_REG_X26,0x10000000),(UC_ARM64_REG_X27,0x20000000)):a.reg_write(reg,v)
    assert run(a,0x1e1cc40,{0x1e1cd68})==0x1e1cd68
    assert struct.unpack('<I',a.mem_read(0x10002078,4))[0]==0x1e0188
print('4/4: Xbox skips the call; linked ARM reaches the call with guest return PC 001E0188.')
