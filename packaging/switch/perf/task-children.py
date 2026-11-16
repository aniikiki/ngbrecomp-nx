"""Instrument the immediate calls of three Xbox update tasks and render-list dispatch."""
import concurrent.futures
from pathlib import Path
import json
import re
import shlex
import subprocess as sp

work = Path('/work/build/switch-runtime/core-perf')
out = work / 'task-children'
out.mkdir(exist_ok=True)
cross = work.parent / 'switch'
cmds = sp.check_output(['ninja', '-t', 'commands', 'ngb-startup'], cwd=cross, text=True)
parents = {'000320E0', '001CB9A0', '00151150', '00308CE0', '00308D50'}
sites = []
def build(unit):
    command = next(shlex.split(row) for row in cmds.splitlines() if row.endswith('/' + unit))
    src = Path(command[-1]).read_text()
    def change(m):
        va, body = m[1], m[0]
        if va not in parents:
            return body
        def wrap(call):
            statement = call[0]
            target = '_icall_target' if 'ICALL_SAFE' in statement else call[1]
            # Fiber hand-off is explicitly accounted for by the runtime.
            if target == '0x0032A293u' or (va.startswith('00308') and target != '_icall_target'):
                return statement
            sites.append((va, target))
            return ('{ unsigned prev_task = ngb_task_enter(' + target + '); ' + statement +
                    ' ngb_task_exit(prev_task); }')
        return re.sub(r'RECOMP_ABI_CALL\((0x[0-9A-F]+u), sub_[0-9A-F]+\);|'
                      r'RECOMP_ICALL_SAFE_AT\(_icall_target, _icall_esp, 0x[0-9A-F]+u\);', wrap, body)
    src = re.sub(r'^void sub_([0-9A-F]+)\(void\)\n\{.*?^\}', change, src, flags=re.M | re.S)
    source = out / unit
    source.write_text('extern unsigned ngb_task_enter(unsigned); extern void ngb_task_exit(unsigned);\n' + src)
    obj = str(source) + '.o'
    command[command.index('-o')+1] = obj
    command[command.index('-MF')+1] = obj+'.d'
    command[-1] = str(source)
    sp.run(command, cwd=cross, check=True)
units = ['recomp_%04d.c'%i for i in (1, 10, 16, 28)]
with concurrent.futures.ThreadPoolExecutor(2) as pool:
    list(pool.map(build,units))
assert set(k for k,v in sites) == parents
(out / 'sites.json').write_text(json.dumps(sorted(sites)))
