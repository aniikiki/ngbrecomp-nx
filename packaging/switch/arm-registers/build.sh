#!/usr/bin/env bash
# Run after a successful normal Direct3D Switch build.
set -euo pipefail
cd "$(dirname "$0")/../../.."
docker run --rm -v "$PWD:/work" -v "${NGB_NXVK_ROOT:-$PWD/../nxvk}:/nxvk:ro" -w /work "${NGB_PERF_SWITCH_IMAGE:-ngb-switch-nxvk:dev}" sh -ec '
  ninja -C build/switch-runtime/switch -j2 ngb-startup
  python3 packaging/switch/arm-registers/compile.py
  python3 packaging/switch/arm-registers/gates.py
  python3 packaging/switch/arm-registers/package.py --rigid-clip'
