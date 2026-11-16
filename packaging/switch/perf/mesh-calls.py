"""Link an offline-only mesh call trace into the real-core combat runner."""
import json
from pathlib import Path
import shlex
import subprocess

scripts = Path(__file__).resolve().parent
core = Path('/work/build/switch-runtime/core-perf')
host = core.parent / 'host'
runtime = scripts.parent / 'runtime'
hooks = runtime / 'direct/hooks.c'
out = core / 'mesh-calls'
out.mkdir(exist_ok=True)
src = hooks.read_text()
def inject(anchor, text):
    global src
    assert src.count(anchor) == 1, anchor
    src = src.replace(anchor, text)
tag = 'void ngb_direct_timing_flip(unsigned completed)\n{'
inject(tag, (scripts / 'mesh-calls.inc').read_text() + '\n' + tag + '\n    mesh_call_frame = completed;')
tag = 'void ngb_direct_mesh_scope(int enter)\n{'
inject(tag, tag + '\n    mesh_call_boundary(enter);')
tag = 'int d3d_hook(int fn)\n{'
inject(tag, tag + '\n    if (mesh_call_active) mesh_event(2, fn, MEM32(esp));')
source = out / 'hooks.c'
source.write_text(src)
commands = subprocess.check_output(['ninja', '-t', 'commands', 'ngb-runtime-test'], cwd=host, text=True)
cc = next(shlex.split(line) for line in commands.splitlines() if line.endswith('/direct/hooks.c'))
cc[-1] = str(source)
obj = str(out / 'hooks.o')
cc[cc.index('-o')+1] = obj
cc[cc.index('-MF')+1] = obj + '.d'
cc[1:1] = ['-I'+str(hooks.parent), '-include', str(runtime/'switch_guest_regs.h')]
subprocess.run(cc, cwd=host, check=True)
link = json.loads((core/'exact-link.json').read_text())
link[link.index(str(core/'exact-hooks.c.o'))] = obj
link[link.index('-o')+1] = str(out/'replay')
subprocess.run(link, cwd=host, check=True)
