"""Offline Clang AArch64 ELF experiment. Build retail hot units unchanged,
against the same device headers and public ABI as the GCC reference objects.
No fast-math, fp contraction, or PC-only register-file definitions."""
from pathlib import Path
import subprocess as sp,concurrent.futures as cf,sys,shutil
p=Path('build/switch-runtime');d=p/'compiler-study';d.mkdir(exist_ok=True)
if not (d/'sysinclude/stdint.h').exists() or not (d/'libnx/switch.h').exists():
 sp.run(['docker','run','--rm','-v',str(Path.cwd())+':/work','-w','/work','ngb-switch-nxvk:dev','sh','-ec','cp -R /opt/devkitpro/devkitA64/aarch64-none-elf/include build/switch-runtime/compiler-study/sysinclude; cp -R /opt/devkitpro/libnx/include build/switch-runtime/compiler-study/libnx'],check=True)
if not (d/'newlib-fpclassify.o').exists():
 sp.run(['docker','run','--rm','-v',str(Path.cwd())+':/work','-w','/work','ngb-switch-nxvk:dev','sh','-ec', 'prefix=/opt/devkitpro/devkitA64/bin/aarch64-none-elf-; lib=$("${prefix}gcc" -print-file-name=libm.a); "${prefix}ar" p "$lib" libm_a-s_fpclassify.o >build/switch-runtime/compiler-study/newlib-fpclassify.o; test -s build/switch-runtime/compiler-study/newlib-fpclassify.o'],check=True)
nums=[0,1,2,3,9,10,11,14,16,27,28,29,37,44]
def build(n):
 src=p/'gen'/f'recomp_{n:04}.c';o=d/(src.stem+'.o')
 cmd=['clang','--target=aarch64-none-elf','-mcpu=cortex-a57','-O2','-g0','-fPIC','-ffunction-sections','-fdata-sections','-fno-strict-aliasing','-fwrapv','-ffp-contract=off','-DNDEBUG','-D__SWITCH__','-D_POSIX_C_SOURCE=200809L','-Wno-parentheses-equality','-Wno-return-type','-Wno-shift-count-negative','-Wno-shift-count-overflow','-Wno-unused-value','-I'+str(d/'sysinclude'),'-I'+str(d/'libnx'),'-I'+str(p/'gen'),'-Ipackaging/switch/runtime','-include','packaging/switch/runtime/switch_guest_regs.h','-c',str(src),'-o',str(o)]
 if src.name in (p/'gen/direct_units.cmake').read_text().split(' ',1)[1].rstrip(')\n').split():cmd.insert(1,'-DNGB_DIRECT3D')
 with (d/(src.stem+'.log')).open('w') as f:sp.run(cmd,check=True,stderr=f)
 print(src.name,o.stat().st_size,flush=True)
with cf.ThreadPoolExecutor(3) as ex:list(ex.map(build,[int(n) for n in sys.argv[1:]] or nums))
