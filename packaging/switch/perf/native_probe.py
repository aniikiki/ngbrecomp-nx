"""Build offline instrumentation against the packaged Switch game's register ABI."""
from pathlib import Path
import json
import shlex
import subprocess

ROOT = Path('/work')
BASE = ROOT / 'build/switch-runtime'
RUNTIME = ROOT / 'packaging/switch/runtime'
REGS = BASE / 'native-regs'


class NativeProbe:
    def __init__(self, name):
        self.host = BASE / 'host'
        self.core = BASE / 'core-perf'
        self.out = self.core / name
        self.out.mkdir(exist_ok=True)
        self.commands = [
            shlex.split(line) for line in subprocess.check_output(
                ['ninja','-t','commands','ngb-runtime-test'], cwd=self.host, text=True
            ).splitlines()
        ]
        self.link = json.loads((self.core / 'exact-link.json').read_text())
        objects = sorted(REGS.glob('recomp_*.c.o'))
        if len(objects) != 14:
            raise ValueError('Expected the fourteen 0.51 private ABI units')
        for obj in objects:
            original = obj.name.replace('.c.o','.o')
            matches = [i for i, v in enumerate(self.link) if v.endswith('/' + original)]
            if len(matches) != 1:
                raise ValueError(f'Expected one original object for {original}: {matches}')
            self.link[matches[0]] = str(obj)
        self.link[1:1] = [str(REGS / (n + '.o')) for n in
                          ('entry','gates','checkpoint','backend-host-clip')]

    def compile(self, name, source, flags=()):
        matches = [c.copy() for c in self.commands if c[-1].endswith('/' + name)]
        if len(matches) != 1:
            raise ValueError(f'Ambiguous or absent compilation command for {name}')
        cmd = matches[0]
        original = Path(cmd[-1])
        path = self.out / original.name
        path.write_text(source)
        obj = str(path) + '.o'
        cmd[cmd.index('-o') + 1] = obj
        cmd[cmd.index('-MF') + 1] = obj + '.d'
        cmd[-1] = str(path)
        cmd[1:1] = ['-I' + str(original.parent), *flags]
        subprocess.run(cmd, cwd=self.host, check=True)
        return obj

    def driver(self, prelude):
        source = (REGS / 'host-driver.c').read_text()
        anchor = 'void __real_ngb_kernel_log'
        assert source.count(anchor) == 1
        obj = self.compile('runtime_test.c', source.replace(anchor, prelude + anchor), [
            '-I' + str(REGS), '-I' + str(RUNTIME), '-include', str(RUNTIME / 'switch_guest_regs.h'),
            '-DNGB_RIGID_CLIP','-DNGB_REGISTER_PACKAGE'
        ])
        self.link[self.link.index(str(self.core / 'exact-runtime_test.c.o'))] = obj

    def add(self, name, source):
        self.link.insert(1, self.compile(name, source))

    def finish(self):
        self.link[self.link.index('-o') + 1] = str(self.out / 'replay')
        subprocess.run(self.link, cwd=self.host, check=True)
