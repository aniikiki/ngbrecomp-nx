"""Build an exclusive Xbox-task clock into the host harness, not the game objects."""
from pathlib import Path
import json
import sys
import shlex
import subprocess as sp

work = Path('/work/build/switch-runtime/core-perf')
host = work.parent / 'host'
runtime = Path('/work/packaging/switch/runtime')
children = '--children' in sys.argv
story = '--story' in sys.argv
out = work / ('story-tasks' if story else 'task-children' if children else 'tasks')
out.mkdir(exist_ok=True)

def replace(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError('cannot identify task boundary: ' + old)
    return source.replace(old, new)

workers = (runtime / 'workers.inc').read_text()
for start in ['static struct worker {', 'static struct fiber {']:
    workers = replace(workers, start, start + '\n    uint32_t saved_task;')
for name in ['dest', 'next']:
    before = f'    ngb_ctx_switch(&old->sp, {name}->sp);'
    workers = replace(workers, before,
                      f'    old->saved_task = task_key; task_set({name}->saved_task);\n' + before)
(out / 'workers.inc').write_text(workers)
impl = (work / 'exact-runtime.inc').read_text()
anchor = 'void ngb_checkpoint(uint32_t va)\n{'
clock = Path(__file__).with_name('task-clock.inc').read_text()
if story:
    clock = "#define NGB_TASK_STORY 1\n" + clock
if children:
    clock += '''
unsigned ngb_task_enter(unsigned child) {
    uint32_t parent = task_key;
    if (parent == 0x001ca790u || parent == 0x001cb9a0u ||
        parent == 0x00151150u || parent == 0x000320e0u)
        task_set(child | 0x80000000u);
    return parent;
}
void ngb_task_exit(unsigned parent) { task_set(parent); }
'''
impl = replace(impl, anchor, clock + '\n' + anchor + '''
    if (va == 0x0030c8b0u) {
        /* Task trampoline: [ESP+4] is its object; object+12 is its callback. */
        uint32_t obj, key;
        const void *p = ngb_ram_span(g_esp + 4, 4);
        if (p) memcpy(&obj, p, 4);
        if (!p || !(p = ngb_ram_span(obj + 12, 4))) task_set(0);
        else { memcpy(&key, p, 4); task_set(key); }
    }''')
anchor = '    RecompRegs saved = g_regs;\n    uint32_t saved_va = current_va;'
impl = replace(impl, anchor, anchor + '\n    uint32_t previous_task = task_key; task_set(1);')
impl = replace(impl, '    return result;\n}\n\nstatic void call_dpc', '    task_set(previous_task);\n    return result;\n}\n\nstatic void call_dpc')
(out / 'tasks-runtime.inc').write_text(impl)
driver = (work / 'exact-test.c').read_text().replace('exact-runtime.inc', 'tasks-runtime.inc')
anchor = '        if (flip == 30 || flip == 120 || flip == 1680'
if story:
    anchor = '        uint64_t cpu=(uint64_t)t.tv_sec'
driver = replace(driver, anchor, '        task_window(flip);\n' + anchor)
src = out / 'test.c'
src.write_text(driver)
cmds = sp.check_output(['ninja', '-t', 'commands', 'ngb-runtime-test'], cwd=host, text=True)
cc = next(shlex.split(row) for row in cmds.splitlines() if row.endswith('/runtime_test.c'))
obj = str(out / 'driver.o')
cc[cc.index('-o') + 1] = obj
cc[cc.index('-MF') + 1] = obj + '.d'
cc[1:1] = ['-include', str(runtime / 'switch_guest_regs.h')]
cc[-1] = str(src)
sp.run(cc, cwd=host, check=True)
link = json.loads((work / 'exact-link.json').read_text())
link[link.index(str(work / 'exact-runtime_test.c.o'))] = obj
if children:
    for name in ('0001', '0010', '0016', '0028'):
        pos = next(i for i,x in enumerate(link) if x.endswith('/recomp_' + name + '.o'))
        link[pos] = str(out / ('recomp_' + name + '.c.o'))
link[link.index('-o') + 1] = str(out / 'replay')
sp.run(link, cwd=host, check=True)
