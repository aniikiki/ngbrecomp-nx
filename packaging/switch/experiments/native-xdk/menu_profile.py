"""Route signed front-end autosaves to the native profile writer on both ARM builds."""
from pathlib import Path
import subprocess


def link_menu_profile(root, output, link, compile_command, cwd, objcopy):
    runtime = root / 'packaging/switch/runtime'
    guest = (root / 'build/switch-runtime/gen/recomp_0028.c').read_text()
    begin = guest.index('void sub_0030F9D0(void)\n{')
    body = guest[begin:guest.index('\n}', begin) + 2]
    body = body.replace('void sub_0030F9D0(void)', 'void ngb_encode_menu_profile(void)')
    # At this point retail has validated, encrypted and signed the full record.
    # Release its temporary using the same helper as a successful WriteFile.
    anchor = '    PUSH32(esp, 0);\n    PUSH32(esp, 0x20);\n    PUSH32(esp, 2);'
    assert body.count(anchor) == 1
    body = body.replace(anchor, '''    if (esi == 1360 && ngb_queue_menu_profile((const void *)ngb_guest_pointer(MEM32(esp + 0x10), esi), esi)) {
        eax = MEM32(esp + 0x10);
        PUSH32(esp, 0x0030FCB3u); RECOMP_ABI_CALL(0x00311140u, sub_00311140);
        esi = 0;
        goto loc_0030FCCC;
    }
''' + anchor)
    header = '''#define RECOMP_GENERATED_CODE
#include "recomp_funcs.h"
#include "files.h"

/* The system-data branch in sub_0030F650 calls the serializer with its
 * caller's return address at +0x230. Both save helpers take six guest
 * arguments, with their own return at +0x24c. Match the two calls from
 * the menu transition sub_0017B650, including the specific invocation
 * of the generic play-time save helper which is also used in gameplay. */
int ngb_is_menu_profile(void)
{
    if (MEM32(esp) != 0x0030F802u || MEM32(esp + 8) != 0xDB9380u || MEM32(esp + 12) != 0x508u)
        return 0;
    uint32_t caller = MEM32(esp + 0x230);
    return (caller == 0x0017B5D2u && MEM32(esp + 0x24c) == 0x0017B6B0u) ||
           (caller == 0x001DB4F4u && MEM32(esp + 0x24c) == 0x0017B722u);
}
'''
    src = output / 'menu-profile.c'
    src.write_text(header + body)
    cc = compile_command.copy()
    cc[1:1] = ['-I' + str(runtime), '-include', str(runtime / 'switch_guest_regs.h'),
               '-Wno-unused-label', '-Wno-unused-but-set-variable', '-Wno-unused-variable']
    obj = output / 'menu-profile.o'
    cc[cc.index('-o') + 1] = str(obj)
    cc[cc.index('-MF') + 1] = str(obj) + '.d'
    cc[-1] = str(src)
    subprocess.run(cc, cwd=cwd, check=True)

    # The PGO unit calls its own serializer. Weaken that symbol in a private
    # copy and retain a second name for all other saves to call directly.
    i = next(i for i, x in enumerate(link) if x.endswith('recomp_0028.c.o'))
    original = 'ngb_reg_sub_0030F9D0'
    retained = output / 'profile-recomp_0028.c.o'
    subprocess.run([str(objcopy), '--add-symbol', 'ngb_retail_profile_encoder=.text.sub_0030F9D0:0,global,function',
                    '--weaken-symbol=' + original, link[i], retained], check=True)
    link[i] = str(retained)
    gate = output / 'menu-profile-gate.o'
    subprocess.run([cc[0], '-c', runtime / 'direct/menu_profile.S', '-o', gate], check=True)
    link[1:1] = [str(gate), str(obj)]
