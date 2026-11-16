#!/usr/bin/env python3
"""Build a host-only ARM probe of the 18 calls inside NGB's mesh submission.

Run in the host build container, after building ngb-runtime-test. The original
objects and the Switch binary stay untouched. Run the printed executable with
the same environment/arguments as the ordinary combat replay.
"""
import argparse
from pathlib import Path
import re
import shlex
import subprocess

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('build', type=Path, help='configured Ninja host build')
ap.add_argument('output', type=Path, help='scratch directory for the instrumented host binary')
ap.add_argument('--chains', action='store_true', help='measure recurring state descriptor lists instead of timing calls')
args = ap.parse_args()
build, out = args.build.resolve(), args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
commands = subprocess.check_output(['ninja', '-t', 'commands', 'ngb-runtime-test'],
                                   cwd=build, text=True).splitlines()
link = shlex.split(commands[-1].split('&&')[1])


def replace_object(filename, edit):
    cmd, = (shlex.split(c) for c in commands if c.endswith('/' + filename))
    original = Path(cmd[-1])
    obj_arg = cmd.index('-o') + 1
    obj = str(out / (filename + '.o'))
    link[link.index(cmd[obj_arg])] = obj
    src = out / filename
    src.write_text(edit(original.read_text()))
    cmd[obj_arg] = obj
    cmd[cmd.index('-MF') + 1] = obj + '.d'
    cmd[-1] = str(src)
    cmd.insert(1, '-I' + str(original.parent))
    subprocess.run(cmd, cwd=build, check=True)


profile = """
#include <time.h>
#include <stdio.h>
#include <string.h>
static unsigned model_serial, hits[32];
static unsigned long long sums[32];
static unsigned long long stamp(void) {
    struct timespec ts;
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);
    return 1000000000ull * ts.tv_sec + ts.tv_nsec;
}
void dump_model(unsigned flip) {
    for (int i = 0; i < 32; ++i) if (hits[i])
        fprintf(stderr, "[MODEL] flip=%u site=%d hits=%u ns=%llu\\n", flip, i, hits[i], sums[i]);
    memset(sums, 0, sizeof sums);
    memset(hits, 0, sizeof hits);
}
"""


def mesh(s):
    match = re.search(r'^void sub_0030BCA0\(void\)\n\{.*?^\}', s, re.M | re.S)
    if args.chains:
        marker = '    RECOMP_ENTRY(0x0030C240u);'
        assert s.count(marker) == 1
        probe = Path(__file__).with_name('profile-model-chains.inc').read_text()
        return s[:match.start()] + probe + s[match.start():].replace(
            marker, '    observe_chain(eax);\n' + marker, 1)
    sites = []

    def wrap(m):
        i = len(sites)
        sites.append(m[0])
        return ('{ unsigned long long t = sel ? stamp() : 0; ' + m[0] +
                f' if (sel) {{ sums[{i}] += stamp() - t; hits[{i}]++; }} }}')

    body = re.sub(r'RECOMP_(?:ABI_CALL|ICALL_SAFE_AT)\([^;]*\);', wrap, match[0])
    assert len(sites) == 18 and body.count('esp += 4; return;') == 1
    body = body.replace('    RECOMP_ENTRY', '    int sel = (++model_serial * 2654435761u >> 27) == 0;\n'
                        '    unsigned long long beg = sel ? stamp() : 0;\n    RECOMP_ENTRY', 1)
    body = body.replace('esp += 4; return;', 'if (sel) { sums[31] += stamp()-beg; hits[31]++; } esp += 4; return;')
    (out / 'sites.txt').write_text('\n'.join(f'{i} {site}' for i, site in enumerate(sites)) + '\n')
    return profile + s[:match.start()] + body + s[match.end():]


def driver(s):
    line = '        if (flip == 1680 || flip == 1800 || flip == 1920) {'
    assert s.count(line) == 1
    return s.replace(line, '        if (flip == 120 || flip == 1680 || flip == 1800 || flip == 1920) {\n'
                     '            extern void dump_model(unsigned); dump_model(flip);\n        }\n' + line)


replace_object('recomp_0028.c', mesh)
replace_object('runtime_test.c', driver)
exe = out / 'model-replay'
link[link.index('-o') + 1] = str(exe)
subprocess.run(link, cwd=build, check=True)
print(exe)
