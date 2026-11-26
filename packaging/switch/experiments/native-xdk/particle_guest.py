"""Install native particle preparation in the Switch register-ABI guest."""
import hashlib
import json
import re
import subprocess


def link_profile(root, output, link, cc):
    gate = output / 'particle-profile.o'
    source = root / 'packaging/switch/runtime/direct/particle_profile.S'
    subprocess.run([cc, '-c', source, '-o', gate], check=True)
    link[1:1] = [str(gate), '-Wl,--wrap=ngb_reg_sub_00123D20,--wrap=ngb_reg_sub_00123D50,--wrap=ngb_reg_sub_00308CE0']


def audit(reference, candidate, objdump):
    def functions(obj):
        dump = subprocess.check_output([objdump, '-dr', obj], text=True)
        parts = re.split(r'^Disassembly of section ([^:]+):\n', dump, flags=re.M)
        return dict(zip(parts[1::2], parts[2::2]))

    old, new = functions(reference), functions(candidate)
    added = sorted(new.keys() - old.keys())
    assert not (old.keys() - new.keys()) and all(name.startswith('.text.particle_') for name in added)
    changed = sorted(name for name in old if old[name].strip() != new[name].strip())
    assert changed == ['.text.sub_001245E0', '.text.sub_001249B0', '.text.sub_00125480'], changed
    data = {'changed_sections': changed, 'native_helpers': added, 'unchanged_sections': len(old) - len(changed),
            'reference_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
            'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest()}
    (candidate.parent / 'particle-guest.json').write_text(json.dumps(data, indent=2) + '\n')


def replace(s, old, new):
    if s.count(old) != 1:
        raise ValueError(f'Particle instruction boundary changed: {old}')
    return s.replace(old, new)


def transform(s):
    # Bind the literal update callbacks installed by the common effect-pool
    # initializer. An unknown target, including one installed during an update,
    # uses the guest's normal checked lookup on that same invocation.
    initializer = s.split('void sub_00123E70(void)\n{', 1)[1].split('\n}', 1)[0]
    calls = initializer.split('RECOMP_ABI_CALL(0x00123DE0u')[:-1]
    targets = set()
    for call in calls:
        pushes = re.findall(r'PUSH32\(esp, ([^();]+)\);', call)
        callback = pushes[-4]
        if re.fullmatch(r'0x[0-9A-F]+', callback):
            targets.add(int(callback, 16))
    assert len(targets) >= 16
    arms = '\n'.join(f'case 0x{va:08X}u: PARTICLE_CALL(sub_{va:08X}); break;'
                     for va in sorted(targets))
    site = 'RECOMP_ICALL_SAFE_AT(_icall_target, _icall_esp, 0x00124930u);'
    direct = '''
#define PARTICLE_CALL(fn) do { \\
    g_icall_trace[g_icall_trace_idx & (ICALL_TRACE_SIZE - 1)] = _icall_target; \\
    ++g_icall_trace_idx; \\
    ++g_icall_count; \\
    RECOMP_ICALL_OBSERVE_SITE(0x00124930u, _icall_target); \\
    RECOMP_ICALL_OBSERVE(_icall_target, RECOMP_ICALL_SEEN_RESOLVED); \\
    RECOMP_ABI_CALL(_icall_target, fn); \\
} while (0)
    switch (RECOMP_ICALL_IS_CODE(_icall_target) ? _icall_target : 0) {
''' + arms + '\n    default: ' + site + '\n    }\n#undef PARTICLE_CALL\n'
    s = replace(s, site, direct)
    s = replace(s, '#include "recomp_funcs.h"', '#include "recomp_funcs.h"\n#include "particle_prepare.h"')
    owner = 'RECOMP_ABI_CALL(0x001BDD10u, sub_001BDD10)'
    s = replace(s, owner, 'if (!particle_unlinked_owner()) ' + owner)
    s = replace(s, 'loc_00124812: ;', 'loc_00124812: ;\n    if (particle_move()) goto particle_age;')
    s = replace(s, '    edi = MEM32(esi + 0x210);\n    SET_LO16(ecx, MEM16(esi + 0x218));',
                'particle_age: ;\n    edi = MEM32(esi + 0x210);\n    SET_LO16(ecx, MEM16(esi + 0x218));')
    for start, end in [('00124ACF', '00124AEF'), ('00124D9D', '00124DBF')]:
        label = 'loc_' + start + ': ;'
        s = replace(s, label, label + f'\n    if (particle_model_matrix(ebp, 0x{end}u)) goto loc_{end};')
    s = replace(s, 'loc_00125520: ; ngb_guest_block_poll();',
                '    if (particle_flat_vertices()) goto loc_0012575E;\n\nloc_00125520: ; ngb_guest_block_poll();')
    state = 'MEM16(ebx + 0xC) = LO16(edx);\n    g_ebp = ebp;'
    s = replace(s, state, state.replace('    g_ebp', '    if (particle_view_position(ebp)) goto loc_00125845;\n    g_ebp'))
    return s
