#!/usr/bin/env python3
"""Package only the explicitly listed test programs, never game assets."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zipfile

root = Path(__file__).resolve().parents[2]
build = root / "build/switch-probe"
package = root / "build/switch-validation"
programs = [build / "ngb-basic-probe.nro"] + [
    build / "nxvk" / f"{name}.nro"
    for name in ("ngb_vk_caps", "nvk_smoke", "nvk_tri", "nvk_textures", "nvk_vi_swapchain")
]

# Validate every input before updating the output directory.
for program in programs:
    data = program.read_bytes()
    if data[16:20] != b"NRO0":
        raise SystemExit(f"Invalid NRO header: {program}")
    size = struct.unpack_from("<I", data, 24)[0]
    if not 0x80 <= size <= len(data):
        raise SystemExit(f"Invalid NRO size: {program}")
    if data[size:size + 4] != b"ASET":
        raise SystemExit(f"Missing NRO assets: {program}")

target = package / "switch/ngb-probe"
target.mkdir(parents=True, exist_ok=True)
outputs = []
for program in programs:
    dest = target / program.name
    shutil.copyfile(program, dest)
    outputs.append(dest)
readme = package / "README.md"
shutil.copyfile(root / "docs/switch-validation.md", readme)
outputs.append(readme)

manifest = {
    "target": "Nintendo Switch / Horizon / AArch64",
    "hardware_validation": "pending user hardware tests",
    "ngb_game_included": False,
    "storage_root": "sdmc:/switch/ngb-probe/",
    "disk_shader_cache": "disabled",
    "base_image": (build / "image.txt").read_text().strip(),
    "nxvk_revision": (build / "nxvk-revision.txt").read_text().strip(),
    "nxvk_image": (build / "nxvk-image.txt").read_text().strip(),
    "base_toolchain": (build / "toolchain.txt").read_text().splitlines(),
}
manifest_path = package / "BUILD.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
outputs.append(manifest_path)
checksums = package / "SHA256SUMS.txt"
checksums.write_text("".join(
    f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(package).as_posix()}\n"
    for path in outputs
))
outputs.append(checksums)

archive = package.with_suffix(".zip")
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for path in outputs:
        z.write(path, path.relative_to(package).as_posix())
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:
        raise SystemExit("ZIP integrity verification failed")
print(archive)
print(f"{len(programs)} NRO files; archive and NRO headers verified; hardware results pending")
