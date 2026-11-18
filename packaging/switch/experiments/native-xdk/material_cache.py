"""Compatibility stamp and portable material seed generation. Never copy a host GPU cache."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

MAGIC = b'NGBD3DC1'
ROOT = Path(__file__).resolve().parents[4]
GENERATOR_INPUTS = ['src/d3d/vk/backend.cpp', 'src/d3d/vk/spirv.cpp', 'src/d3d/vk/spirv.h',
                    'src/d3d/gpu/shaders.cpp', 'src/d3d/gpu/shaders.h', 'src/d3d/gpu/state.h',
                    'src/d3d/gpu/vertex.cpp', 'src/d3d/gpu/vertex.h']


def compatibility():
    sources = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in GENERATOR_INPUTS}
    # The version also covers the compiler options in spirv.cpp and raw PipeKey ABI.
    digest = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()[:20]
    return {'epoch': 'materials-v1-' + digest, 'generator_sources': sources}


def records(path, spirv=False):
    b = path.read_bytes()
    assert b[:8] == MAGIC, path
    offset = 8
    while offset < len(b):
        if spirv:
            key, count = struct.unpack_from('<QI', b, offset)
            size = count * 4
            start = offset + 12
            kind = b'S'
        else:
            kind, key, size = struct.unpack_from('<cQI', b, offset)
            start = offset + 13
        assert start + size <= len(b), (path, offset, size)
        data = b[start:start + size]
        if spirv:
            words = struct.unpack('<' + 'I' * count, data)
            assert len(words) >= 5 and words[0] == 0x07230203
            end = 5
            while end < len(words):
                n = words[end] >> 16
                assert n, (path, offset, end)
                end += n
            assert end == len(words)
        yield kind, key, data
        offset = start + size


def merge(inputs, output, extra_spirv):
    info = compatibility()
    modules, pipes, spirv = {}, set(), {}
    provenance = {}
    for directory in inputs:
        assert directory.name == info['epoch'], (directory, info['epoch'])
        for kind, key, data in records(directory / 'recipes.bin'):
            if kind == b'S':
                assert len(data) == 9 and data[8] in (0, 1)
                assert key not in modules or modules[key] == data, ('conflicting module', hex(key))
                modules[key] = data
            elif kind == b'K':
                # LP64 on both the ARM host collector and Switch.
                assert len(data) == 256, len(data)
                pipes.add(data)
        for path in (directory / 'recipes.bin', directory / 'spirv.bin'):
            provenance[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in [*(p / 'spirv.bin' for p in inputs), *extra_spirv]:
        for _, key, data in records(path, spirv=True):
            assert key not in spirv or spirv[key] == data, ('conflicting source', hex(key))
            spirv[key] = data
        provenance[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    # Reject orphan dependencies rather than shipping a seed that silently warms
    # only some of the recorded states. Include internal passes, not just materials.
    for data in pipes:
        vs, ps = struct.unpack_from('<QQ', data)
        assert vs in modules and ps in modules, ('missing module', hex(vs), hex(ps))
    sources = {struct.unpack_from('<Q', data)[0] for data in modules.values()}
    assert sources <= spirv.keys(), ('missing SPIR-V', [hex(h) for h in sources - spirv.keys()])
    output.mkdir(parents=True, exist_ok=False)
    recipes = MAGIC + b''.join(struct.pack('<cQI', b'S', key, len(data)) + data for key, data in sorted(modules.items()))
    recipes += b''.join(struct.pack('<cQI', b'K', 0, len(data)) + data for data in sorted(pipes))
    code = MAGIC + b''.join(struct.pack('<QI', key, len(spirv[key]) // 4) + spirv[key] for key in sorted(sources))
    (output / 'materials.recipes').write_bytes(recipes)
    (output / 'materials.spirv').write_bytes(code)
    info.update(modules=len(modules), pipelines=len(pipes), sources=len(sources), inputs=provenance,
                recipe_sha256=hashlib.sha256(recipes).hexdigest(), spirv_sha256=hashlib.sha256(code).hexdigest())
    (output / 'manifest.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps({k: info[k] for k in ('epoch', 'modules', 'pipelines', 'sources')}, indent=2))


def report(directory, seed=None, zero=False):
    sessions = []
    for line in (directory / 'materials.csv').read_text().splitlines():
        kind, *values = line.split(',')
        if kind == '#SESSION':
            sessions.append({'epoch': values[0], 'miss_frames': [], 'warm': [], 'end': []})
            sessions[-1].update({k: int(v) for k, v in (x.split('=') for x in values[1:])})
        elif kind == 'M':
            assert len(values) == 7
            sessions[-1]['miss_frames'].append(dict(zip(
                ('present', 'time_us', 'draws', 'modules', 'pipelines', 'sources', 'compile_us'), map(int, values))))
        elif kind in ('W', 'END'):
            sessions[-1]['warm' if kind == 'W' else 'end'].append({k: int(v) for k, v in (x.split('=') for x in values)})
    assert sessions and all(len(s['warm']) == len(s['end']) == 1 for s in sessions), 'incomplete session'
    for s in sessions:
        assert s['warm'][0]['failed'] == s['end'][0]['lost'] == s['end'][0]['io_errors'] == 0, s
        s['totals'] = {k: sum(f[k] for f in s['miss_frames']) for k in ('modules', 'pipelines', 'sources', 'compile_us')}
        s['max_compile_us'] = max((f['compile_us'] for f in s['miss_frames']), default=0)
    answer = {'sessions': sessions}
    if seed:
        known = {(k, h, data) for k, h, data in records(seed / 'materials.recipes')}
        actual = {(k, h, data) for k, h, data in records(directory / 'recipes.bin') if k in (b'S', b'K')}
        answer['coverage'] = {'recorded': len(actual), 'covered': len(actual & known), 'missing': len(actual - known)}
        assert actual <= known, answer['coverage']
    if zero:
        assert all(s['totals']['modules'] == s['totals']['pipelines'] == 0 for s in sessions), 'runtime creation remained'
    return answer


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--merge', type=Path, nargs='+')
    p.add_argument('--spirv', type=Path, nargs='*', default=[])
    p.add_argument('--output', type=Path)
    p.add_argument('--report', type=Path)
    p.add_argument('--seed', type=Path)
    p.add_argument('--expect-zero', action='store_true')
    args = p.parse_args()
    if args.report:
        answer = report(args.report, args.seed, args.expect_zero)
        if args.output:
            args.output.write_text(json.dumps(answer, indent=2) + '\n')
        print(json.dumps([{k: v for k, v in s.items() if k != 'miss_frames'} for s in answer['sessions']], indent=2))
    elif args.merge:
        assert args.output
        merge([x.resolve() for x in args.merge], args.output.resolve(), [x.resolve() for x in args.spirv])
    else:
        print(json.dumps(compatibility(), indent=2))
