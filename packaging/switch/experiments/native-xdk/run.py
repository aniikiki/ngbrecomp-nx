"""Headless ARM replay in Docker with isolated saves and no desktop/audio access."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path, help='new report directory under build/')
parser.add_argument('--control', action='store_true')
parser.add_argument('--checks', action='store_true')
parser.add_argument('--newgame', action='store_true')
parser.add_argument('--attract', action='store_true', help='leave the controller idle for the title battle demo')
parser.add_argument('--diagnostics', action='store_true')
parser.add_argument('--binary', type=Path, help='use an archived replay executable under build/')
parser.add_argument('--seconds', type=int, default=150)
parser.add_argument('--cache', type=Path, help='isolated persistent cache root under build/; default: OUTPUT/cache')
parser.add_argument('--seed', type=Path, help='portable seed directory made by material_cache.py')
parser.add_argument('--effects', action='store_true', help='exercise jump/heavy/charged attacks in Alma')
parser.add_argument('--msaa', type=int, choices=(1, 2, 4), default=1)
parser.add_argument('--scale', type=int, choices=(1, 2), default=1)
parser.add_argument('--material', choices=('0', '1', 'ab'), default='1', help='native material path or within-run ABBA comparison')
parser.add_argument('--mesh', choices=('0', '1', 'ab'), default='1')
parser.add_argument('--mesh-verify', action='store_true', help='verify prepared state and every skipped recorder range')
args = parser.parse_args()
assert not args.diagnostics or not (args.control or args.checks)
assert not args.attract or not (args.newgame or args.checks)
root = Path(__file__).resolve().parents[4]
output = args.output.resolve()
assert output.is_relative_to(root / 'build'), 'reports and scratch saves belong under build/'
output.mkdir(parents=True, exist_ok=False)
seed = root / 'build/switch-runtime/core-perf/wide-start/newgame-hdd2'
shutil.copytree(seed, output / 'hdd')
base = root / 'build/switch-runtime/core-perf/native-xdk'
binary = base / ('replay-control' if args.control else 'replay-checks' if args.checks else 'replay-diag' if args.diagnostics else 'replay')
if args.binary:
    binary = args.binary.resolve()
    assert binary.is_relative_to(root / 'build') and binary.is_file()
env = {
    'NGB_D3D_NATIVE': '0' if args.control else '1', 'NGB_D3D_THREAD': '1',
    'SDL_AUDIODRIVER': 'dummy', 'NGB_AUDIO': '0', 'EGL_PLATFORM': 'surfaceless',
    'VK_ICD_FILENAMES': '/usr/share/vulkan/icd.d/lvp_icd.aarch64.json', 'LP_NUM_THREADS': '4',
    'NGB_DIRECT_SPIRV': '/work/build/switch-runtime/direct/cache/spirv.bin',
    'XDG_CACHE_HOME': '/work/build/switch-runtime/core-perf/native-xdk/' + ('control-cache' if args.control else 'cache'),
    'NGB_REPLAY_SECONDS': str(args.seconds),
    'NGB_REPLAY_MSAA': str(args.msaa),
    'NGB_D3D_SCALE': str(args.scale),
    'NGB_NATIVE_MATERIAL': args.material,
    'NGB_NATIVE_MESH': args.mesh,
    'NGB_D3D_SEED': '/work/build/no-material-seed',
}
cache = (args.cache or output / 'cache').resolve()
assert cache.is_relative_to(root / 'build')
cache.mkdir(parents=True, exist_ok=True)
env['NGB_D3D_CACHE'] = '/work/' + str(cache.relative_to(root))
env['XDG_CACHE_HOME'] = '/work/' + str((output / 'driver-cache').relative_to(root))
if args.seed:
    seed = args.seed.resolve()
    assert seed.is_relative_to(root / 'build')
    manifest = json.loads((seed / 'manifest.json').read_text())
    from material_cache import compatibility
    assert manifest['epoch'] == compatibility()['epoch'], 'seed belongs to a different renderer'
    env['NGB_D3D_SEED'] = '/work/' + str((seed / 'materials.recipes').relative_to(root))
    env['NGB_DIRECT_SPIRV'] = '/work/' + str((seed / 'materials.spirv').relative_to(root))
if args.effects:
    assert not (args.attract or args.newgame or args.checks)
    env['NGB_REPLAY_EFFECTS'] = '1'
    env['NGB_REPLAY_XBOX_LAYOUT'] = '1'
if args.mesh_verify:
    env['NGB_NATIVE_MESH_VERIFY'] = '1'
if not args.checks:
    env['NGB_REPLAY_ATTRACT' if args.attract else 'NGB_REPLAY_NEWGAME' if args.newgame else 'NGB_REPLAY_ALMA'] = '1'
command = ['docker', 'run', '--rm', '-v', f'{root}:/work', '-w', '/work/' + str(output.relative_to(root))]
for key, value in env.items(): command += ['-e', f'{key}={value}']
command += ['ngb-switch-host:direct0331', 'timeout', str(args.seconds + 120),
            '/work/' + str(binary.relative_to(root)), '/work/game_files', './hdd']
with (output / 'log.txt').open('w') as log:
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
text = (output / 'log.txt').read_text(errors='replace')
passed = result.returncode == 0 and ('[CONTRACT-PASS]' if args.checks else '[REPLAY-PASS]') in text
report = {'passed': passed, 'exit_code': result.returncode, 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
          'environment': env, 'command': command}
if binary.with_suffix('.build.json').exists():
    report['build'] = json.loads(binary.with_suffix('.build.json').read_text())
    assert report['build']['binary_sha256'] == report['binary_sha256'], 'binary changed during replay'
(output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
print(('PASS' if passed else 'FAIL'), output)
raise SystemExit(0 if passed else 1)
