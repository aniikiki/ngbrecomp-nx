"""Check the experimental AArch64 guest register ABI against a retail stack adjustment.

Run in the devkitA64 container from the checkout after staging the game.
Does not modify the game's source, build objects or the packaged NRO.
"""
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

root = Path.cwd()
build = root / 'build/switch-runtime/switch'
unit = build.parent / 'gen/recomp_0000.c'
runtime = root / 'packaging/switch/runtime'
commands = subprocess.check_output(['ninja', '-t', 'commands', 'ngb-startup'], cwd=build, text=True)
base = next(shlex.split(line) for line in commands.splitlines() if line.endswith('/' + unit.name))
source = unit.read_text()
first = source.index('void sub_00011000(void)\n{')
start = source.index('void sub_00018A60(void)\n{')
end = source.index('\n}', start) + 2
body = source[start:end]
ret_label = 'loc_00019B0D:'
assert 'esp = esp + 4;' in body.split(ret_label, 1)[1].split('/* ucomiss */', 1)[0]
names = ('eax', 'ecx', 'edx', 'esp', 'ebx', 'esi', 'edi')
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    regs = d / 'regs.h'
    regs.write_text('#include "switch_guest_regs.h"\n' + ''.join(
        f'#undef g_{r}\nregister unsigned gp_{r} asm("x{i}");\n#define g_{r} gp_{r}\n'
        for i, r in enumerate(names, 19)))
    mem = (runtime / 'guest_memory.h').read_text()
    anchor = 'extern unsigned char *ngb_fast_ram;'
    assert mem.count(anchor) == 1
    (d / 'guest_memory.h').write_text(mem.replace(anchor, anchor + '''
register unsigned char *reg_ram asm("x26");
register uint16_t *reg_pages asm("x27");
#define ngb_fast_ram reg_ram
#define ngb_fast_page_bytes reg_pages
'''))
    # Make all register updates explicitly observable at translated call boundaries.
    barrier = '__asm__ __volatile__("" : ' + ', '.join('"+r"(gp_' + r + ')' for r in names) + ' : : "memory")'
    preamble = source[:first] + '\n#undef RECOMP_ABI_CALL\n#define RECOMP_ABI_CALL(va,fn) do { ' + barrier + '; (fn)(); ' + barrier + '; } while(0)\n'
    local = d / unit.name
    local.write_text(preamble + body + '\n')
    for label, extra in [('default', []), ('private ABI', ['-fno-ipa-ra'])]:
        args = base.copy()
        asm = d / 'function.s'
        args[args.index('-c')] = '-S'
        args[args.index('-o') + 1] = str(asm)
        args[args.index('-MF') + 1] = str(d / 'deps')
        args[1:1] = ['-I' + str(d), '-include', str(regs)]
        args[-1:] = ['-g0', '-ffixed-x28', '-fno-optimize-sibling-calls', *extra, str(local)]
        subprocess.run(args, cwd=build, check=True)
        s = asm.read_text()
        # 0x19B0D is the pushed retail return address (mov + movk).
        anchor = re.search(r'\bmov\s+w\d+,\s*39693\b', s)
        if not anchor:
            raise SystemExit('Compiler instruction shape changed; inspect the guest return address manually')
        block = s[anchor.end():]
        call = re.search(r'\bbl\s+sub_0001A300\b', block)
        parity = re.search(r'\bbl\s+recomp_parity8\b', block)
        if not (call and parity and call.end() < parity.start()):
            raise SystemExit('Expected call sequence not found; audit the compiler output')
        ok = bool(re.search(r'\badd\s+w22,\s*w22,\s*#?4\b', block[call.end():parity.start()]))
        print(f'{label}: caller stack adjustment {"present" if ok else "absent"}')
        if extra and not ok:
            raise SystemExit('Guest stack cleanup lost; do not use this register ABI')
