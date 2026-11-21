"""Build an isolated native-XDK player NRO; never deploy or overwrite the stable package.

Run in ngb-switch-nxvk:dev after build.py guest. Reuse the retained player
packager so its settings, movie, shader-cache and diagnostics options stay intact.
"""
from pathlib import Path
import hashlib
import json
import sys
from material_cache import compatibility

root = Path('/work')
diagnostics = '--diagnostics' in sys.argv
version = '0.57.24'
(root / 'build/switch-runtime/history').mkdir(parents=True, exist_ok=True)
assert '--seed' in sys.argv, 'supply the validated portable material seed with --seed'
seed = Path(sys.argv[sys.argv.index('--seed') + 1]).resolve()
assert seed.is_relative_to(root / 'build')
seed_manifest = json.loads((seed / 'manifest.json').read_text())
assert seed_manifest['epoch'] == compatibility()['epoch'], 'rebuild the seed for this renderer'
assert hashlib.sha256((seed / 'materials.recipes').read_bytes()).hexdigest() == seed_manifest['recipe_sha256']
assert hashlib.sha256((seed / 'materials.spirv').read_bytes()).hexdigest() == seed_manifest['spirv_sha256']
epoch_header = root / 'build/switch-runtime/core-perf/native-xdk/material_epoch.h'
epoch_header.write_text('#define NGB_D3D_CACHE_EPOCH "' + seed_manifest['epoch'] + '"\n')
experiment = Path(__file__).resolve().parent
opening = experiment.parent / 'opening'
source = (opening / 'package-retained.py').read_text()
assert source.count("seeds=base/'core-perf/opening-present-combined'") == 1
source = source.replace("seeds=base/'core-perf/opening-present-combined'",
                        'seeds=base/' + repr(str(seed.relative_to(root / 'build/switch-runtime'))))
source = source.replace('opening-complete.spirv', 'materials.spirv').replace('opening-120.recipes', 'materials.recipes')
anchor = "sys.argv=['submit-bound-device.py'"
assert source.count(anchor) == 1
inject = '''
replace("version='0.56.25';out=", "version='@VERSION@';out=")
replace(" def comp(name,s,flags=[]):", """ def comp(name,s,flags=[]):
  flags=[*flags,'-DNGB_NATIVE_XDK']
  if name=='files_bridge.c':
   flags=[*flags,'-DNGB_COMBAT_PERF']
  if name=='vk/backend.cpp':
   from story_gpu import instrument
   s=instrument(s,wave=@WAVE@)
   flags=[*flags,'-include','/work/build/switch-runtime/core-perf/native-xdk/material_epoch.h']
  if name=='main.c':
   (d/'native_combat_perf.inc').write_text((root/'combat_perf.inc').read_text().replace('#SESSION,0.56.25,','#SESSION,@VERSION@,'))
   s=s.replace('#include \\"combat_perf.inc\\"','#include \\"native_combat_perf.inc\\"')""")
replace(" regs=[]", " from disc_archives import link_disc_archives\\n disc_hooks=link_disc_archives(Path('/work'),d,link)\\n regs=[]")
replace(" handlers=[n for n in table", " assert all(name in table for name in disc_hooks)\\n handlers=[n for n in table")
replace("  regs.append(obj)", "  if u in (28,44,45): obj=base/'core-perf/native-xdk'/f'recomp_{u:04}.c.o'\\n  regs.append(obj)")
replace(" assert (out/'linked-inputs.txt').read_bytes()==(base/'core-perf/opening-pixel-link-audit/linked-inputs.txt').read_bytes()", """ reference={Path(line.split()[1]).name:line for line in (base/'core-perf/native-xdk/retained-inputs.txt').read_text().splitlines()}
 actual={Path(line.split()[1]).name:line for line in (out/'linked-inputs.txt').read_text().splitlines()}
 assert len(actual)==47 and all(actual[n]==reference[n] for n in actual if n not in ('recomp_0028.c.o','recomp_0044.c.o','recomp_0045.c.o'))
 assert all('core-perf/native-xdk/' in actual[n] for n in ('recomp_0028.c.o','recomp_0044.c.o','recomp_0045.c.o'))""")
'''
inject = inject.replace('@VERSION@', version).replace('@WAVE@', str(diagnostics))
if diagnostics:
    inject = inject.replace("flags=[*flags,'-DNGB_NATIVE_XDK']",
        "flags=[*flags,'-DNGB_NATIVE_XDK','-DNGB_NATIVE_DIAG']\n  if name in ('hle.cpp','threaded.cpp'):\n   flags=[*flags,'-DNGB_COMBAT_PERF','-include',str(root/'combat_perf.h')]")
source = source.replace(anchor, inject + '\n' + anchor)
source = source.replace("exec(compile(s,'submit-bound-device.py'", "Path('/work/build/switch-runtime/core-perf/native-xdk/package-expanded.py').write_text(s)\nexec(compile(s,'submit-bound-device.py'")
sys.argv = [str(opening / 'package-retained.py'), '--hardware-test', '--pipe-attribution',
            '--opening-warm', '--texture-preload', '--player']
exec(compile(source, str(opening / 'package-retained.py'), 'exec'), {'__file__': str(opening / 'package-retained.py')})

out = root / 'build/switch-runtime/history' / version
inputs = [root / 'src/d3d/native_device.inc', root / 'src/d3d/native_material.inc', root / 'src/d3d/hle.cpp',
          root / 'src/d3d/gpu/threaded.cpp', root / 'src/d3d/gpu/readback.h', root / 'src/d3d/vk/backend.cpp']
inputs += [root / 'src/d3d' / n for n in ('native_diag.h','native_diag.inc','native_pacing.h')]
inputs += [root / 'src/d3d' / n for n in ('native_mesh.inc','native_simple.inc','gpu/prepared.h','gpu/backend.h')]
inputs += [root / 'packaging/switch/runtime/direct' / n for n in ('native_mesh.inc','native_model.inc','display.h','display_device.h','presenter.inc','platform.cpp')]
inputs += [root / 'packaging/switch/runtime' / n for n in ('runtime.c','direct/hooks.c','direct/output.h','scene/bridge.c')]
inputs += [root / 'packaging/switch/runtime' / n for n in ('main.c','settings_panel.inc','scanout.c','scanout.h','combat_perf.h','combat_perf.inc','workers.inc')]
inputs += [experiment / n for n in ('build.py','package.py','material_cache.py','material_guest.py','story_gpu.py','disc_archives.py')]
inputs += [root / 'packaging/switch/runtime/direct/disc_archives.S']
inputs += [root / 'packaging/switch/runtime' / n for n in ('files.c','files.h','files_bridge.c','files_bridge.h','disc_reads.inc','ohci_boot.c')]
if diagnostics:
    inputs += [experiment / 'story_gpu.inc']
inputs += [root / 'build/switch-runtime/core-perf/native-xdk/retained-inputs.txt']
inputs += [root / 'src/d3d/vk/cache_writer.h', root / 'src/d3d/vk/quick_menu.inc', opening / 'hardware-prewarm.py', opening / 'package-retained.py']
inputs += [opening / n for n in ('command-record.py', 'batch-bytes.py')]
inputs += [seed / n for n in ('materials.recipes','materials.spirv','manifest.json')]
manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
manifest['material_cache'] = compatibility()
manifest['nro_sha256'] = hashlib.sha256((out / 'ngb-startup.nro').read_bytes()).hexdigest()
manifest['removed_xdk_bodies'] = len(json.loads((root / 'build/switch-runtime/core-perf/native-xdk/intercepted.json').read_text()))
material_guest = root / 'build/switch-runtime/core-perf/native-xdk/material-guest.json'
manifest['native_material'] = json.loads(material_guest.read_text())
assert manifest['native_material']['all_other_assembly_unchanged']
assert manifest['native_material']['candidate_sha256'] == hashlib.sha256(
    (material_guest.parent / 'recomp_0028.c.o').read_bytes()).hexdigest()
assert f'#SESSION,{version},'.encode() in (out / 'ngb-startup.nro').read_bytes()
if diagnostics:
    assert b'#V,native_frame,entry_us,' in (out / 'ngb-startup.nro').read_bytes()
    assert b'#I,issue_us,read_start_us,read_end_us,' in (out / 'ngb-startup.nro').read_bytes()
    assert b'#W,submit_frame,strip_draws,' in (out / 'ngb-startup.nro').read_bytes()
    assert b'#A,submit_frame,material_detail,' in (out / 'ngb-startup.nro').read_bytes()
    assert b'#L,submit_frame,phase,texture_sig,' in (out / 'ngb-startup.nro').read_bytes()
    assert b'#Y,begin_us,generation_after_acquire,' in (out / 'ngb-startup.nro').read_bytes()
(out / 'native-build.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('Native package verified:', out)
