"""Isolated full-XDK replacement replay, using the packaged ARM guest objects.

Run 'guest' in ngb-switch-nxvk:dev, then 'host' in ngb-switch-host:direct0331.
Generated game code stays under the ignored build tree. Neither step deploys.
"""
from pathlib import Path
import hashlib
import json
import re
import shlex
import subprocess as sp
import sys
from material_cache import compatibility
from disc_archives import link_disc_archives

root = Path('/work')
base = root / 'build/switch-runtime'
out = base / 'core-perf/native-xdk'
out.mkdir(exist_ok=True)
runtime = root / 'packaging/switch/runtime'
experiment = Path(__file__).resolve().parent
full = base / 'core-perf/opening-full-page'

if sys.argv[1] == 'guest':
    # Strict coverage includes unnamed library entries, not only the 94 API hooks.
    counts = {}
    for unit in (44, 45):
        name = f'recomp_{unit:04}.c'
        src = (base / 'gen' / name).read_text()
        def intercept(m):
            address = int(m[1], 16)
            if not 0x3c5260 <= address < 0x3d48a1:
                return m[0]
            counts[address] = counts.get(address, 0) + 1
            # Remove the whole XDK function body, including its FIFO and
            # resource-management implementation. There is no fallback body.
            return f'ngb_d3d_native_entry(0x{address:08x}u);\n}}'
        src = re.sub(r'RECOMP_ENTRY\(0x([0-9A-Fa-f]+)u\);.*?\n}', intercept, src, flags=re.S)
        (out / name).write_text('extern int ngb_d3d_native_entry(unsigned);\n' + src)
    assert len(counts) == 226 and all(n == 1 for n in counts.values()), counts
    (out / 'intercepted.json').write_text(json.dumps(sorted(counts), indent=2) + '\n')
    script = (root / 'packaging/switch/arm-registers/compile.py').read_text().split("f=o/'entry.S'")[0]
    script = script.replace("o=Path(os.environ.get('NGB_REG_OUT',w.parent/'native-regs'))", f'o=Path({str(out)!r})')
    script, n = re.subn(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))', script, flags=re.M)
    assert n == 1
    script = script.replace(r'(?:sub_|d3d_orig_)[0-9A-F]+', r'(?:(?:sub_|d3d_orig_)[0-9A-F]+|xbe_entry_point)')
    script = script.replace("(r/'guest_memory.h').read_text()", f"Path({str(full / 'template.h')!r}).read_text()")
    script = script.replace('register uint16_t *reg_pages asm("x27");', 'register uint32_t *reg_ends asm("x27");')
    script = script.replace('#define ngb_fast_page_bytes reg_pages', '')
    script = script.replace(' sp.run(c,cwd=w,check=True)', " c[-1]=str(o/n);c[1:1]=['-I'+str(w.parent/'gen')]\n sp.run(c,cwd=w,check=True)")
    script = script.replace('ex.map(build,units)', "ex.map(build,['recomp_0044.c','recomp_0045.c'])")
    exec(compile(script, 'native-xdk-guest', 'exec'), {})
    cc = '/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc'
    # The register synchronisation is already in the assembly emitted above.
    # Keeping it explicit needs no changes to the shared exit-gate table.
    for unit in (44, 45):
        name = f'recomp_{unit:04}.c'
        sp.run([cc, '-c', out / (name + '.s'), '-o', out / (name + '.o')], check=True)
    from material_guest import build as build_material_guest
    build_material_guest(root, out)
    print('Intercepted', len(counts), 'D3D library entries; material bridges retain the shipped PGO object.')
elif sys.argv[1] == 'host':
    control = '--control' in sys.argv
    checks = '--checks' in sys.argv
    diagnostics = '--diagnostics' in sys.argv
    push_diagnostics = '--push-diagnostics' in sys.argv
    record_prewarm = '--record-prewarm' in sys.argv
    assert '--cpu-ab' not in sys.argv, 'The rejected CPU experiment is archived with cpu-ab-battle/experimental-sources.'
    assert not diagnostics or not (control or checks)
    host = base / 'host'
    sources = out / 'host-sources'
    sources.mkdir(exist_ok=True)
    commands = [shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-runtime-test'], cwd=host, text=True).splitlines()]
    link = json.loads((base / 'core-perf/exact-link.json').read_text())
    link = [x for x in link if not x.startswith('-Wl,--wrap=')]
    link.insert(1, '-no-pie')
    link[1:1] = ['-Wl,--wrap=ngb_poll_due', '-Wl,--wrap=ngb_scanout_direct', '-Wl,--wrap=d3d_hook']
    if checks: link[1:1] = ['-Wl,--wrap=ngb_graphics_callback', '-Wl,--wrap=volkLoadDeviceTable']
    manifest = {}
    # The retained guest inputs must survive cleanup of old release packages.
    for line in (out / 'retained-inputs.txt').read_text().splitlines():
        digest, name = line.split()
        path = base / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
        manifest[path.name] = path
    assert len(manifest) == 47
    for i, value in enumerate(link):
        if 'ngb_boot_code.dir/' in value and re.search(r'recomp_\d{4}\.o$', value):
            name = Path(value).stem + '.c.o'
            link[i] = str(out / name if not control and name in ('recomp_0028.c.o','recomp_0044.c.o','recomp_0045.c.o') else manifest[name])
    link[1:1] = [str(full / 'entry.o'), str(full / 'gates.o'), str(base / 'native-regs/checkpoint.o')]
    prologue_flags = []
    if not control:
        # Use the player's Sofdec hooks so New Game exercises the native decoder in replays.
        start, caption = 'ngb_reg_sub_003443D0', 'ngb_reg_sub_00344AD0'
        link.insert(1, f'-Wl,--wrap={start},--wrap={caption}')
        prologue_flags = [f'-DNGB_PROLOGUE_START={start}', f'-DNGB_PROLOGUE_CAPTION={caption}',
                          '-DNGB_PROLOGUE_CLEAR=ngb_reg_sub_00231EB0']
        link_disc_archives(root, out, link)
        from menu_profile import link_button_prompts, link_menu_profile
        link_menu_profile(root, out, link, next(c for c in commands if c[-1].endswith('/runtime_test.c')), host, 'objcopy')
        link_button_prompts(root, out, link, 'objcopy')
    def compile_source(name, source=None, flags=()):
        if name == 'ohci_boot.c':
            # Some recorded scripts supply Xbox buttons directly.
            flags = [*flags, '-DNGB_REPLAY_PAD_LAYOUT']
        if name == 'vk/backend.cpp':
            flags = [*flags, '-DNGB_D3D_CACHE_EPOCH="' + compatibility()['epoch'] + '"']
            if record_prewarm:
                source = (root / 'src/d3d/vk/backend.cpp').read_text()
                at = source.index('void VulkanBackend::Prewarm() {')
                before, warm = source[:at], source[at:]
                needle = '                if (m) { modules_[r.key] = m; ++made; }'
                assert warm.count(needle) == 1
                warm = warm.replace(needle, "                if (m) { modules_[r.key] = m; ++made; CacheRecord('S', r.key, d, 9); }")
                needle = '            if (!m) continue;  // Leave first use free to retry.'
                assert warm.count(needle) == 1
                warm = warm.replace(needle, needle + '\n            CacheModule(r.key, hlsl, vertex);')
                needle = '                    pipes++;'
                assert warm.count(needle) == 1
                warm = warm.replace(needle, needle + "\n                    CacheRecord('K', 0, &k, sizeof(k));")
                source = before + warm
        if diagnostics:
            if name == 'vk/backend.cpp':
                from story_gpu import instrument
                source = instrument(source if source is not None else (root / 'src/d3d/vk/backend.cpp').read_text())
            flags = [*flags, '-DNGB_NATIVE_DIAG', '-DNGB_COMBAT_PERF', '-include', str(runtime / 'combat_perf.h')]
        matches = [c.copy() for c in commands if c[-1].endswith('/' + name)]
        assert len(matches) == 1, (name, len(matches))
        cmd = matches[0]
        original = Path(cmd[-1])
        path = original
        if source is not None:
            path = sources / original.name
            path.write_text(source)
        obj = out / (original.name + '.o')
        cmd[cmd.index('-o') + 1] = str(obj)
        cmd[cmd.index('-MF') + 1] = str(obj) + '.d'
        cmd[-1] = str(path)
        cmd[1:1] = ['-I' + str(original.parent), *flags]
        sp.run(cmd, cwd=host, check=True)
        return str(obj)
    driver = (experiment / 'replay.c').read_text()
    if diagnostics:
        (sources / 'native_combat_perf.inc').write_text((runtime / 'combat_perf.inc').read_text().replace('#SESSION,0.56.25,','#SESSION,0.57.37,'))
    runtime_source = (runtime / 'runtime.c').read_text().replace('RECOMP_TLS RecompRegs g_regs;', 'RecompRegs g_regs;')
    runtime_source = runtime_source.replace('        ngb_menu_draw(cursor);', '        extern void replay_unlock(uint32_t); replay_unlock(g_ebx);\n        ngb_menu_draw(cursor);')
    (sources / 'native-runtime.inc').write_text(runtime_source)
    test_flags = ['-DNGB_NATIVE_CONTRACT_TEST', '-I' + str(experiment)] if checks else []
    if push_diagnostics: test_flags += ['-DNGB_NATIVE_PUSH_DIAG']
    obj = compile_source('runtime_test.c', driver, ['-I' + str(sources), '-I' + str(runtime), '-include', str(runtime / 'switch_guest_regs.h'), '-DNGB_REGISTER_PACKAGE', *test_flags])
    link[link.index(str(base / 'core-perf/exact-runtime_test.c.o'))] = obj
    # Replace object inputs already present in the old link, or precede archives.
    for name, source, flags in [
        ('files.c', None, ()), ('files_bridge.c', None, ()), ('identity.c', None, ()), ('opening_movie.c', None, prologue_flags),
        ('ohci_boot.c', None, ()), ('pgraph_boot.c', None, ('-Wno-unused-variable',)),
        ('nv2a_boot.c', None, ()),
        ('scanout.c', None, ()),
        ('vm.c', (full / 'vm.c').read_text(), ()),
        ('contiguous.c', (full / 'contiguous.c').read_text(), ()),
        ('direct/hooks.c', None, ('-include', str(runtime / 'switch_guest_regs.h'))),
        ('hle.cpp', None, test_flags),
        ('threaded.cpp', None, ()), ('gpu/shaders.cpp', None, ()),
        ('direct/platform.cpp', None, ()),
        ('scene/bridge.c', None, ()), ('vk/backend.cpp', None, ('-DNGB_RIGID_CLIP',)),
    ]:
        obj = compile_source(name, source, flags)
        old = [i for i,v in enumerate(link) if v.endswith('/' + Path(name).name + '.o') or
               (name == 'direct/hooks.c' and v.endswith('/exact-hooks.c.o'))]
        if old:
            assert len(old) == 1, (name, old)
            link[old[0]] = obj
        else:
            link.insert(1, obj)
    if checks:
        cmd = next(c.copy() for c in commands if c[-1].endswith('/vk/backend.cpp'))
        obj = out / 'test_submission.o'
        cmd[cmd.index('-o') + 1] = str(obj)
        cmd[cmd.index('-MF') + 1] = str(obj) + '.d'
        cmd[-1] = str(experiment / 'test_submission.cpp')
        sp.run(cmd, cwd=host, check=True)
        link.insert(1, str(obj))
    executable = out / ('replay-control' if control else 'replay-checks' if checks else 'replay-diag' if diagnostics else 'replay')
    link[link.index('-o') + 1] = str(executable)
    (out / 'link.json').write_text(json.dumps(link, indent=2) + '\n')
    result = sp.run(link, cwd=host, text=True, stdout=sp.PIPE, stderr=sp.STDOUT)
    (out / 'link.log').write_text(result.stdout)
    if result.returncode:
        errors = sorted(set(re.findall(r'undefined reference to [^\n]+|multiple definition of [^;\n]+', result.stdout)))
        print('\n'.join(errors[:60]) if errors else result.stdout[:5000])
        raise SystemExit(result.returncode)
    inputs = [root / n for n in ('src/d3d/hle.cpp','src/d3d/native_device.inc','src/d3d/native_material.inc','src/d3d/gpu/threaded.cpp',
              'src/d3d/gpu/readback.h','src/d3d/vk/backend.cpp','packaging/switch/runtime/runtime.c',
              'packaging/switch/runtime/direct/hooks.c','packaging/switch/runtime/direct/output.h',
              'packaging/switch/runtime/scene/bridge.c')]
    inputs += [root / 'src/d3d' / n for n in ('native_diag.h','native_diag.inc','native_pacing.h')]
    inputs += [root / 'src/d3d/vk/cache_writer.h']
    inputs += [root / 'src/d3d' / n for n in ('native_mesh.inc','native_simple.inc','gpu/prepared.h','gpu/backend.h')]
    inputs += [runtime / 'direct' / n for n in ('native_mesh.inc','native_model.inc','disc_archives.S','menu_profile.S','button_prompts.S')]
    inputs += [runtime / 'button_prompts.c']
    inputs += [runtime / n for n in ('workers.inc','diagnostics_flag.h','combat_perf.h','combat_perf.inc','files.c','files.h','files_bridge.c','files_bridge.h','disc_reads.inc','disc_names.inc','ohci_boot.c','ohci_boot.h','opening_movie.c','prologue_stream.inc','menu_profile.inc')]
    inputs += [runtime / n for n in ('movie_audio.inc','audio_output.h','audio_output.inc')]
    if diagnostics:
        inputs += [experiment / 'story_gpu.inc']
    inputs += list(experiment.glob('*.py')) + [experiment / n for n in ('replay.c','native_contract.inc','native_lifetime_contract.inc','native_header_contract.inc','native_effect_contract.inc','test_pacing.cpp','test_combat_writer.c','test_material.cpp','test_mesh.cpp','test_simple.cpp')]
    inputs += [experiment / n for n in ('native_submission_contract.inc','native_shader_contract.inc','test_submission.cpp')]
    metadata = {**compatibility(), 'record_prewarm': record_prewarm,
                'binary_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                'sources': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    executable.with_suffix('.build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('Linked', executable)
else:
    raise SystemExit('expected guest or host')
