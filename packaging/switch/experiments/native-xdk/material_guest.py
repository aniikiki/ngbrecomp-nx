"""Retain shipped PGO bodies; bridge native material, mesh and model entries."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys


def build(root, out):
    opening = root / 'packaging/switch/experiments/opening'
    path = opening / 'partition-pgo.py'
    source = path.read_text()
    start = source.index('out=trained.parent/')
    end = source.index(';out.mkdir', start)
    retained = out.parent / 'native-material-pgo'
    source = source[:start] + 'out=Path(' + repr(str(retained)) + ')' + source[end:]
    source = source.replace('for u in (2,10,16,28,29)', 'for u in (28,)')
    source = source.replace("for f in out.glob('recomp_*.s'):f.unlink()", '')
    saved = sys.argv
    try:
        sys.argv = [str(path)]
        exec(compile(source, str(path), 'exec'), {'__file__': str(path)})
    finally:
        sys.argv = saved
    name = 'recomp_0028.c'
    reference = root / 'build/switch-runtime/core-perf/opening-partition-pgo' / (name + '.o')
    original = retained / (name + '.o')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(original) == digest(reference), 'PGO reproduction differs from the shipped object'
    original_source = (retained / (name + '.gated.s')).read_text()
    source = original_source
    bridges = []
    store = '\tstp w19, w20, [x28]\n\tstp w21, w22, [x28, 8]\n\tstp w23, w24, [x28, 16]\n\tstr w25, [x28, 24]\n'
    load = store.replace('stp', 'ldp').replace('str', 'ldr')
    redirects = (
        ('0030B7E0', 'material_fixed', 'material', 2),
        ('0030BA30', 'material_texture', 'material', 4),
        ('00317D10', 'model_lights', 'mesh', 2),
    )
    def restore_calls(text):
        for address, label, _, _ in redirects:
            text = text.replace('ngb_' + label + '_bridge', 'ngb_reg_sub_' + address)
        return text

    for address, label, mode, sites in redirects:
        target = 'ngb_' + label + '_bridge'
        source, count = re.subn(r'(\bbl\s+)ngb_reg_sub_' + address + r'(?=\s*\n)', r'\g<1>' + target, source)
        # GCC duplicates the two call sites in hot/cold and unrolled paths.
        assert count == sites, (address, count)
        bridges.append(f'''
.section .text.{target},"ax",%progbits
.p2align 2
.type {target},%function
{target}:
 adrp x16,ngb_native_{mode}_enabled
 ldr w16,[x16,:lo12:ngb_native_{mode}_enabled]
 cbnz w16,2f
 b ngb_reg_sub_{address}
2:
 stp x29,x30,[sp,-16]!
 mov x29,sp
{store} bl ngb_direct_{label}
 mov w16,w0
{load} ldp x29,x30,[sp],16
 cbnz w16,1f
 b ngb_reg_sub_{address}
1:
 ret
.size {target},.-{target}
''')
    # The old helpers remain available for within-run comparison and DF=1.
    # No other code, cold partition, register allocation or exit gate changes.
    restored = restore_calls(source)
    assert restored == original_source
    # Keep every caller (including other guest units) on the same public/private
    # entry. Only the original function's label/size are renamed; its body and
    # cold partition stay byte-for-byte available to the ABBA control.
    entries = [('0030BCA0', 'mesh'), ('003078B0', 'model'), ('00307A10', 'model_filtered'),
               ('00308D50', 'render_list')]
    for address, label in entries:
        public = 'ngb_reg_sub_' + address
        reference_label = public + '_reference'
        assert source.count(public + ':\n') == 1
        source = source.replace(public + ':\n', reference_label + ':\n')
        kind = '\t.type\t' + public + ', %function'
        assert source.count(kind) == 1
        source = source.replace(kind, '\t.type\t' + reference_label + ', %function')
        size = '\t.size\t' + public + ', .-' + public
        assert source.count(size) == 1
        source = source.replace(size, '\t.size\t' + reference_label + ', .-' + reference_label)
        # Recursive control calls use GCC's local alias. Keep them on the
        # retained traversal when the public entry falls back.
        alias = f'.set\tsub_{address}.localalias,{public}\n'
        if label == 'render_list':
            assert source.count(alias) == 1
            source = source.replace(alias, alias.replace(public, reference_label))
        bridges.append(f'''
.section .text.ngb_native_{label},"ax",%progbits
.p2align 2
.global {public}
.type {public},%function
{public}:
 adrp x16,ngb_native_mesh_enabled
 ldr w16,[x16,:lo12:ngb_native_mesh_enabled]
 cbnz w16,2f
 b {reference_label}
2:
 stp x29,x30,[sp,-16]!
 mov x29,sp
{store} bl ngb_direct_{label}
 mov w16,w0
{load} ldp x29,x30,[sp],16
 cbnz w16,1f
 b {reference_label}
1:
 ret
.size {public},.-{public}
''')
    restored = restore_calls(source)
    for address, _ in entries:
        restored = restored.replace('ngb_reg_sub_' + address + '_reference', 'ngb_reg_sub_' + address)
    assert restored == original_source, 'native entries changed retained PGO bodies'
    assembly = out / (name + '.material.s')
    assembly.write_text(source + ''.join(bridges))
    subprocess.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc', '-c', assembly,
                    '-o', out / (name + '.o')], check=True)
    (out / 'material-guest.json').write_text(json.dumps({
        'baseline_sha256': digest(reference), 'reproduced_sha256': digest(original),
        'candidate_sha256': digest(out / (name + '.o')),
        'redirected_calls': [address for address, _, _, _ in redirects],
        'replaced_entries': [address for address, _ in entries],
        'all_other_assembly_unchanged': True}, indent=2) + '\n')
