"""Attribution within the original cooperative guest, for *offline* replay only."""
from pathlib import Path


def prepare(runtime_source, workers_source, out):
    def replace(s, old, new):
        if s.count(old) != 1:
            raise ValueError('Source layout changed: ' + old)
        return s.replace(old,new)
    w = workers_source
    for kind in ('worker','fiber'):
        anchor = 'static struct ' + kind + ' {'
        w = replace(w,anchor,anchor+'\n    unsigned saved_task;')
    for target in ('dest','next'):
        anchor = f'    ngb_ctx_switch(&old->sp, {target}->sp);'
        w = replace(w,anchor,
                    f'    old->saved_task=dep_task; dep_task={target}->saved_task; dep_key(dep_task);\n'+anchor)
    (out/'workers.inc').write_text(w)
    s = runtime_source
    anchor = 'void ngb_checkpoint(uint32_t va)\n{'
    s = replace(s,anchor,anchor+'''
    if(va==0x0030c8b0u){ unsigned obj=read32(g_esp+4);
        dep_task=read32(obj+12); dep_key(dep_task); }
''')
    anchor = '    RecompRegs saved = g_regs;\n    uint32_t saved_va = current_va;'
    s = replace(s,anchor,anchor+'\n    unsigned prior=dep_task; dep_task=0; dep_key(0);')
    anchor = '    return result;\n}\n\nstatic void call_dpc'
    s = replace(s,anchor,'    dep_task=prior; dep_key(prior);\n'+anchor)
    s = replace(s,'ngb_vm_init(ram);','ngb_vm_init(ram);dep_bind(ram);')
    decl = '#include <stdint.h>\nstatic uint32_t read32(uint32_t);\nvoid dep_bind(void*);void dep_key(unsigned);unsigned dep_task;\n'
    (out/'flow-runtime.inc').write_text(decl+s)
