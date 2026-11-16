#!/usr/bin/env python3
"""Stage upstream probes with all storage confined to the test directory."""
from pathlib import Path
import shutil
import sys

nxvk = Path(sys.argv[1])
root = Path(__file__).resolve().parents[2]
stage = root / "build/switch-probe/nxvk-sources"
stage.mkdir(parents=True, exist_ok=True)
smoke = nxvk / "switch/smoke"
for pattern in ("*.c", "*.h"):
    for source in smoke.glob(pattern):
        shutil.copyfile(source, stage / source.name)
shutil.copytree(smoke / "shaders", stage / "shaders", dirs_exist_ok=True)
shutil.copyfile(root / "packaging/switch/probe/vulkan.c", stage / "ngb_vk_caps.c")

# A standalone test must not read the upstream runner's state or chainload it.
(stage / "nvk_chain.c").write_text("/* Standalone NGB probes do not use the NXVK chainloader. */\n")
for pattern in ("*.c", "*.h"):
    for path in stage.glob(pattern):
        source = path.read_text()
        path.write_text(source.replace("sdmc:/", "sdmc:/switch/ngb-probe/logs/"))

harness = stage / "nvk_harness.h"
source = harness.read_text()
anchor = '   g_nvk_log = fopen(path, "w");'
if source.count(anchor) != 1:
    raise SystemExit("NXVK logging hook changed; review storage adaptation")
source = source.replace("#include <switch.h>", "#include <switch.h>\n#include <sys/stat.h>")
source = source.replace(anchor, '''   mkdir("sdmc:/switch", 0777);
   mkdir("sdmc:/switch/ngb-probe", 0777);
   mkdir("sdmc:/switch/ngb-probe/logs", 0777);
   setenv("MESA_SHADER_CACHE_DISABLE", "true", 1);
   setenv("MESA_SHADER_CACHE_DIR", "sdmc:/switch/ngb-probe/cache", 1);
   setenv("MESA_LOG_FILE", "sdmc:/switch/ngb-probe/logs/mesa-runtime.log", 1);
''' + anchor)
harness.write_text(source)

link_script = (nxvk / "switch/build/build-nro.sh").read_text()
anchor = 'SMOKE="$SRC/switch/smoke"'
if link_script.count(anchor) != 1:
    raise SystemExit("NXVK build script changed; review staged-source selection")
link_script = link_script.replace(anchor, 'SMOKE=/ngb/build/switch-probe/nxvk-sources')
(stage / "build-nro.sh").write_text(link_script)
print(f"Staged probes in {stage}; disk shader cache disabled; logs confined to ngb-probe")
