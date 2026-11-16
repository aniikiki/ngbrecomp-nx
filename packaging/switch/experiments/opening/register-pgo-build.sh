#!/bin/sh
# Isolated from the package; expects previously built native-regs and exact-link.json.
set -eu
cd "$(dirname "$0")/../../../.."
d=build/switch-runtime/core-perf/opening-register-pgo
p=packaging/switch/experiments/opening
host(){ docker run --rm -v "$PWD:/work" -w /work ngb-switch-host:direct0331 "$@"; }
cross(){ docker run --rm -v "$PWD:/work" -w /work -e NGB_REG_OUT="/work/$d" -e NGB_REG_PROFILE="$1" ngb-switch-nxvk:dev sh -ec '
 p=packaging/switch/arm-registers
 if [ "$NGB_REG_PROFILE" = train ]; then cp "$(/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc -print-file-name=libgcov.a)" "$NGB_REG_OUT/gcov.a"; fi
 python3 "$p/compile.py";python3 "$p/gates.py"'; }
mkdir -p "$d"
host python3 "$p/register-pgo.py" base
cross train
host python3 "$p/register-pgo.py" train
host sh "$p/run-register-pgo.sh" train training
cross use
host python3 "$p/register-pgo.py" use
for item in base:A1 use:B1 use:B2 base:A2; do host sh "$p/run-register-pgo.sh" "${item%:*}" "${item#*:}"; done
python3 "$p/register-pgo-report.py" "$d/A1.log" "$d/B1.log" "$d/B2.log" "$d/A2.log"
