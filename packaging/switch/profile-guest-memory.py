#!/usr/bin/env python3
"""Build a host-only probe for dynamic scalar memory in nine sampled combat hotspots.

Run in the ARM host container with the configured host build and a scratch directory.
Use NGB_TEST_IDLE_SCENE=combat and the same arguments as ngb-runtime-test.
"""
import argparse
import concurrent.futures
import re
import shlex
import subprocess as sp
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('build', type=Path)
ap.add_argument('output', type=Path)
args = ap.parse_args()
b, p = args.build.resolve(), args.output.resolve()
p.mkdir(parents=True, exist_ok=True)
g = b.parent / 'gen'
commands = sp.check_output(['ninja', '-t', 'commands', 'ngb-runtime-test'], cwd=b, text=True).splitlines()
link = shlex.split(commands[-1].split('&&')[1])
funcs=['0013D330','00140AF0','00149CB0','00308BF0','0030BCA0','003078B0','000298F0','00034E70','00142910']
# Count dynamic scalar macro evaluations only; direct, vector and prevalidated bulk accesses are excluded.
declar='extern unsigned mem_trace_on; extern unsigned long long mem_classes[9][6];\n'
helper=declar+'''static inline __attribute__((always_inline)) uintptr_t watch_scalar(uint32_t a,size_t n,unsigned id,int literal) {
 if(mem_trace_on&&!literal){ unsigned kind=a>=0x8000&&a<0x01000000?0:a>=0x03e00000&&a<0x04000000?1:a>=0x01000000&&a<0x03e00000?2:a>=0x80000000&&a<0x84000000?3:4;
 ++mem_classes[id][kind]; if((uint32_t)(a-g_esp+2048)<4096)++mem_classes[id][5];}
 return ngb_guest_scalar(a,n);
}
'''
tasks = []
found = set()
for source in g.glob('recomp_*.c'):
    body = source.read_text()
    # The inline probe must be declared before the first instrumented function.
    first = True
    for address in sorted(funcs, key=lambda n: body.find('void sub_' + n + '(void)\n{')):
        match = re.search('^void sub_' + address + r'\(void\)\n\{.*?^\}', body, re.S | re.M)
        if not match:
            continue
        define = (f'\n#define ngb_guest_scalar(a,n) watch_scalar((a),(n),{funcs.index(address)},'
                  '__builtin_constant_p(a))\n')
        patch = (helper if first else '') + define + match[0] + '\n#undef ngb_guest_scalar\n'
        body = body[:match.start()] + patch + body[match.end():]
        first = False
        found.add(address)
    if not first:
        tasks.append((source.name, body))
assert found == set(funcs), 'A sampled guest function is missing from the generated code'
f=Path(__file__).resolve().parent / 'runtime/runtime_test.c';s=f.read_text();s=s.replace('void __real_ngb_kernel_log', 'unsigned mem_trace_on; unsigned long long mem_classes[9][6];\nvoid __real_ngb_kernel_log',1)
s=s.replace('        if (flip == 1680', '''        if(flip==1800) mem_trace_on=1;
        if(flip==1920){mem_trace_on=0;for(unsigned i=0;i<9;i++) {fprintf(stderr,"[MEMCLASS] %u",i);for(unsigned j=0;j<6;j++)fprintf(stderr," %llu",mem_classes[i][j]);fprintf(stderr,"\\n");}}
        if (flip == 1680''');tasks.append((f.name,s))

def unit(task):
    name, source = task
    cmd, = (shlex.split(line) for line in commands if line.endswith('/' + name))
    original = Path(cmd[-1])
    text = p / ('memory-' + name)
    obj = str(text) + '.o'
    dest = cmd.index('-o') + 1
    old = cmd[dest]
    text.write_text(source)
    cmd[dest] = obj
    cmd[cmd.index('-MF') + 1] = obj + '.d'
    cmd[-1] = str(text)
    cmd.insert(1, '-I' + str(original.parent))
    sp.run(cmd, cwd=b, check=True)
    return old, obj


with concurrent.futures.ThreadPoolExecutor(3) as pool:
    for old, obj in pool.map(unit, tasks):
        link[link.index(old)] = obj
(p / 'columns.txt').write_text('function indexes: ' + ' '.join(funcs) +
                               '\ncounts: image bootstrap VM low-physical-alias other near-ESP(+/-2 KiB, overlaps)\n')
link[link.index('-o') + 1] = str(p / 'memory')
sp.run(link, cwd=b, check=True)
