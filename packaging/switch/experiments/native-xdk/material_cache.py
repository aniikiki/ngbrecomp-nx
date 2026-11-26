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
                    'src/d3d/vk/combat_effects.h', 'src/d3d/vk/glow_filter.h', 'src/d3d/vk/glow_options.h',
                    'src/d3d/gpu/shaders.cpp', 'src/d3d/gpu/shaders.h', 'src/d3d/gpu/state.h',
                    'src/d3d/gpu/vertex.cpp', 'src/d3d/gpu/vertex.h']


def compatibility():
    sources = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in GENERATOR_INPUTS}
    # These revisions add distinct keys for the signed texture view, modulated
    # particles, quad gathers and clamped P8 texel reads. Soft A8 quads select an existing bilinear
    # shader. The mission border, nonuniform haze and point coverage variants have distinct keys.
    epoch_sources = sources.copy()
    backend = 'src/d3d/vk/backend.cpp'
    shader = 'src/d3d/gpu/shaders.cpp'
    header = 'src/d3d/gpu/shaders.h'
    bounds = 'src/d3d/vk/combat_effects.h'
    compatible = {
        # 0.57.72 adds distinct pixel keys for vertex-colour lines, black fog and zero-alpha rejection.
        ('eaf73c90743fe2bacd2945c5cd6ed50a188e78a24a5fa350e98aed30a10ec3e1',
         'a304703cbf66f9ef9d132d1d0112c65d2e50b572f740dec9958e22ac8eb58528',
         'aa7b9481b365b1ce1bf3ecf4b38daa288a8c6e715e5c387e313173c55fa08281',
         '3289cfe9301e18bcb90f06a8bbd90919ee7ef18c0a4836bbf8346b48d02d14cc'),
        ('8ddaebf3c992a429038d4db4db9a58c3328f289f69eb97ea42a45303231617b2',
         '3c2739f5642414f6816e064ff2316ca2f65d04c4c0fcff93357ddf1ef489b2bd',
         'cc59d339e1768bdfdbdf38531f369775089a8f07368e7161c2d29758ad8acea9',
         '85d57bb9ffe5ba6c70a954b0a9201fced94be865aa1f84e40f22b69d290f477e'),
        ('db49869c739a1e24defc48375f80fe8d3d7ece91251772384c3d693456863f0f',
         'b9021672d4bc654f12c1d8d7d1f90b5c7e9c0680479d78e8ba116f065a008afe',
         '9cfd436bfd3986ffc698347f70f0779daeb9f460297446b02d88c3bf592802a6',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        ('2f5dd1900e91ab8faab0aa026fc61e2a3a08bd82a1812e27df69a902874035a1',
         'f1933f21b2c5c4d532550490be72563e5f820282f5318bbcdc4fdcd4c1742c8e',
         'd241b842d4cf10c66a8ca6829259b2cacb93a01733e0e49d8d99768db1fbd987',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        ('c39167f0070c717a2ce3c6782a252a27552e7443a2c186274fda95c23c2ac2a3',
         '94a9bcacb86ad2adee58eea72e427f6041dcbfde2784245f6b30892c8f55e315',
         '32aaf3524849fca1b71ca944f6f6b0c1dd69806f9325aedf383e25df9736eed8',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        ('b7f7bfa2cd4fc2cd33e68aa082879d5ce7969d793788bad7604ec05932a77107',
         '982d249862a0874460627ae00c962ac4c65b7a5e873dd06e3dfe17d5e861463f',
         '657357b495700f6007d6117e7426187b0d69bca6c895c230d9e2497985e6432f',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        ('b18774a205c59ffb810a17b4e9416b81d763399b7efbd19392efec7c8e829886',
         'adb3e50536bab736857caf3e83be148a77859602a6068cd088807e25bd961be7',
         'bd3a516b9cf6faea59a2632c72e130c961731bbe0f06f8872d70b57c2dfdab00',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        ('4f3433e57b4d041cb0404bcd8408c595d2c1581249fd32bb03b9525d765771ca',
         'adb3e50536bab736857caf3e83be148a77859602a6068cd088807e25bd961be7',
         'bd3a516b9cf6faea59a2632c72e130c961731bbe0f06f8872d70b57c2dfdab00',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        ('2a74b2317dfa7eca86d96defab8d14081745403bb6f56b127dc576eec705ae68',
         'f7b2edfabb2dc6c6f02c0e53c8f2ab946f0b4eb4ea75e36ae23444a33204a510',
         '5fd8c3314c21be2088578f11819993a348e0c388f776de2c529f16171dd37211',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        ('998d2791a252682e4099b6f0a0be6489203045d47e12d01ba37104afb6306b85',
         '45afd0850fca1ecb36853828370f60b2beb633cb43e97b4ab6a7c3aa78c0f3f4',
         'db0389332911d8b987801d2cc3ea08fd10d121b7768f85d66c4fa9e7c401890b',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        # 0.57.52 only changes diagnostic counters and text logging.
        ('59b2039b9d75d7098bc2527a31744d0d3d739b41872c5b2a46060542a925d0ca',
         '45afd0850fca1ecb36853828370f60b2beb633cb43e97b4ab6a7c3aa78c0f3f4',
         'db0389332911d8b987801d2cc3ea08fd10d121b7768f85d66c4fa9e7c401890b',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        # 0.57.57 moves the same shader and pipeline recipes to the loading screen.
        ('cb59da27e78f4dabbf88b81d2ad30909c66861868c7ba66411ec5d6882a12f3c',
         '45afd0850fca1ecb36853828370f60b2beb633cb43e97b4ab6a7c3aa78c0f3f4',
         'db0389332911d8b987801d2cc3ea08fd10d121b7768f85d66c4fa9e7c401890b',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        # 0.57.58 uses distinct keys for mipmapped displacement and the water's disabled alpha test.
        ('fe77b05971d28484d7e2889f5d70c02b57beac7502936f7cc6440c89779f2650',
         '8e4f3c48945427f0a95995f5a79b55ba54fac0caffef9e3932c878a47e2eba9a',
         '9f71bcc1c57d84699275cec4241991604ab8ee138ad6a3f7e843f9a9a580aa9e',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        # 0.57.59 adds separate keys for instanced billboard transforms and colours.
        ('dfacc9580ceb65907a568bb5c2d7c712d69f87acf423b61bfa48d8f006a8e622',
         'e1a59623208598b5634ca85ae7d4d10367cc6a871ef0ea33782afc078e7b2b23',
         '95d8049d64808b5efb69b70db3931513864bd43cad9be21c463bc5a274b9336c',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        # 0.57.60 selects existing coordinate keys for unread billboard stages.
        ('b844505d4dfba7402440ab2bf559aebff25d90efadf149066d2cabb7de740b44',
         '69ca18a986ed8d8a622787928941daea8cb2a8c0691b3f2dcc05a5570b1269ec',
         'dd025add898ec7e28c0ec844cd9ac672dce0849d1d2d2922a0beeb168d2300bb',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
        # 0.57.67 reuses the same shaders for ordered particle strips and omits unread constants.
        ('1eaa89e2459dca353ff10497302f70e89988832469f8076f34605e7e73c2db04',
         '1a6b9b0e985ab076d66d90a98da278834310d9d5aa09a7c6e360d0b605b286fb',
         'b572384868b12a61d6984eec51f348d946c2496b947024fc1cdd015eea8e8c90',
         'c9793cec316e6f5eeefbfa4c36289be03a9b21fba30ab953af572c5634d785d9'),
        # 0.57.65 selects keyed particle inputs and folds full-weight crossfades.
        ('4f9cc0d143ffd40fcfa6bb726cd0c52fefb344aff657e8a7473be22804d85927',
         '1a6b9b0e985ab076d66d90a98da278834310d9d5aa09a7c6e360d0b605b286fb',
         'b572384868b12a61d6984eec51f348d946c2496b947024fc1cdd015eea8e8c90',
         'c9793cec316e6f5eeefbfa4c36289be03a9b21fba30ab953af572c5634d785d9'),
        # 0.57.64 adds keyed vertex culling and two alpha-threshold pixel shaders.
        ('7ce7bcee2cf9fa2e753018f7ebc271111dcaf8cfb3ad02fc04168b1b2d38e075',
         '36703fcf3413a3682634a4030d5ef950d53290b61c23cf1f45eb81ada1bfc973',
         'ea664e85b7bd414867b1f22297adb0c35439883119a13278fd5fcb97e9624396',
         'afc17518c17c0c12ee0bf94c24ebf1c2a5561c2ceb28cf02372831d8b35834b4'),
        # 0.57.63 adds separate keys for unlit additive materials and their coverage variants.
        ('0b510d92a82a6ce9c048204f8dbea48969c33746c9c303b175792745aca8778d',
         '421a6188dbcaa982fab2760ce6775fca1eea0a2a527969d11aecf372aef93fcd',
         '31cae2d378cd92f3335b5853f38762e7923a07b1667d46b3c730e1820ff31093',
         'afc17518c17c0c12ee0bf94c24ebf1c2a5561c2ceb28cf02372831d8b35834b4'),
        # 0.57.61 changes geometry residency and reuses the existing line-list pipeline key.
        ('bafb14f1512a9e5a255456c1af3557f592939dd916a8f9cd69bcb4a7b044da1c',
         '69ca18a986ed8d8a622787928941daea8cb2a8c0691b3f2dcc05a5570b1269ec',
         'dd025add898ec7e28c0ec844cd9ac672dce0849d1d2d2922a0beeb168d2300bb',
         '49e9804d6b13fe67dd11f861317cd1ac5988f6a8970390438fd0093583bb757f'),
    }
    if tuple(sources[n] for n in (backend, shader, header, bounds)) in compatible:
        epoch_sources[bounds] = '85d57bb9ffe5ba6c70a954b0a9201fced94be865aa1f84e40f22b69d290f477e'
        epoch_sources[backend] = 'd125a6cd45cfc84f64b900bc0c7a8258922722e9c2812e912efac780085772c2'
        epoch_sources[shader] = '947cbf13fa11dae76dd574d957aa2ec43283234de3344f09c8c132e5afc1c094'
        epoch_sources[header] = 'c0dcde43ba650b496c786c8fc62e7827ed7cbc70d3241e9c80a3a12385c5f771'
    if epoch_sources[backend] == 'd125a6cd45cfc84f64b900bc0c7a8258922722e9c2812e912efac780085772c2':
        epoch_sources[backend] = 'd6d10274541fe37750d0610f9c0fe6dff39b4a32ffcf2ae34af64afedf3280db'
    # The version also covers the compiler options in spirv.cpp and raw PipeKey ABI.
    digest = hashlib.sha256(json.dumps(epoch_sources, sort_keys=True).encode()).hexdigest()[:20]
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
