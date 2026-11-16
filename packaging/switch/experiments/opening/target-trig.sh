#!/bin/sh
set -eu
t=/opt/devkitpro/devkitA64/bin/aarch64-none-elf
m=$("$t-gcc" -print-file-name=libm.a)
d=/work/build/switch-runtime/core-perf/opening-target-trig
mkdir -p "$d"; tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT; cd "$tmp"
"$t-ar" x "$m" libm_a-s_cos.o libm_a-s_sin.o libm_a-k_cos.o libm_a-k_sin.o libm_a-e_rem_pio2.o libm_a-k_rem_pio2.o libm_a-s_floor.o libm_a-s_scalbn.o libm_a-s_fabs.o
"$t-ld" -r ./*.o -o bundle.o
test -z "$("$t-nm" -u bundle.o)"
"$t-nm" -g --defined-only bundle.o | awk '{print $3,"ngb_dev_"$3}' > rename
"$t-objcopy" --redefine-syms=rename bundle.o "$d/trig.o"
