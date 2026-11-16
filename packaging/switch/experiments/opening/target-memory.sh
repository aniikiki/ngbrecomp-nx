#!/bin/sh
set -eu
t=/opt/devkitpro/devkitA64/bin/aarch64-none-elf
m=$("$t-gcc" -print-file-name=libc.a)
d=/work/build/switch-runtime/core-perf/opening-target-memory
mkdir -p "$d"; tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT; cd "$tmp"
"$t-ar" x "$m" libc_a-memcpy.o libc_a-memset.o libc_a-memcmp.o
"$t-ld" -r ./*.o -o bundle.o
test -z "$("$t-nm" -u bundle.o)"
"$t-nm" -g --defined-only bundle.o | awk '{print $3,"ngb_dev_"$3}' > rename
"$t-objcopy" --redefine-syms=rename bundle.o "$d/memory.o"
