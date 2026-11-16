"""Execute the production mission confirm handler and icon branch with isolated guest memory."""
from pathlib import Path
import subprocess as sp, tempfile, runpy
root=Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp)
    menu=(root/'src/main_menu.c').read_text()
    unit=(root/'build/switch-runtime/gen/recomp_0018.c').read_text()
    icons=runpy.run_path(str(root/'packaging/switch/settings/link.py'))['technique_icons'](unit)
    (d/'handlers.inc').write_text(menu[menu.index('static uint8_t mission_bits('):menu.index('/**\n * sub_001764F0')]+menu[menu.index('void sub_00176E30(void)\n{'):menu.index('\n}',menu.index('void sub_00176E30(void)\n{'))+2]+
        icons)
    sp.run(['cc','-O1','-I'+tmp,'-Ibuild/switch-runtime/gen','-Ixboxrecomp/src','-Ixboxrecomp/src/kernel','-Ipackaging/switch/runtime','packaging/switch/fixes/guest.c','-o',d/'test'],cwd=root,check=True)
    sp.run([d/'test'],check=True)
