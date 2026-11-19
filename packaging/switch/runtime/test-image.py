#!/usr/bin/env python3
"""Exercise the actual XBE loader with private copies of a supplied game file.

Only the renderer/memory registration callbacks are stubbed. The file reading,
section mapping and kernel import relocation are taken directly from runtime.c.
No game data or generated code is written into the source tree.
"""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('xbe', type=Path)
    args = parser.parse_args()
    original = args.xbe.read_bytes()
    u32 = lambda offset: struct.unpack_from('<I', original, offset)[0]
    base, headers = u32(0x104), u32(0x108)
    count, table = u32(0x11c), u32(0x120) - base
    source = Path(__file__).with_name('runtime.c').read_text()
    loader = source[source.index('static uint32_t le32('):source.index('static void initialize_thread(')]
    harness = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define RAM_BYTES (64u * 1024u * 1024u)
#define THUNK_BASE 0xfe000000u
#define GUEST_TICK_COUNT 0x7060u
static unsigned char *ram;
static int trap_null;
static uint8_t image_resident[RAM_BYTES / 4096];
static uint16_t image_pins[RAM_BYTES / 4096];
static ptrdiff_t g_xbox_mem_offset;
static uint32_t g_xbox_code_lo, g_xbox_code_hi, thunk_ordinals[512];
static unsigned thunk_count;
static char stopped_reason[256];
static void note(const char *format, ...) { (void)format; }
static void ngb_contiguous_set_ram(void *p) { assert(p == ram); }
static void ngb_scene_memory(void *p, size_t n) { assert(p == ram && n == 2u * RAM_BYTES); }
static uint32_t read32(uint32_t address) {
    assert(address <= RAM_BYTES - 4);
    uint32_t v; memcpy(&v, ram + address, 4); return v;
}
static void write32(uint32_t address, uint32_t value) {
    assert(address <= RAM_BYTES - 4); memcpy(ram + address, &value, 4);
}
'''
    harness += loader + r'''
int main(int argc, char **argv) {
    assert(argc == 3);
    int ok = load_image(argv[1]);
    if (ok) {
        /* Compare the mapped sections, excluding the deliberately changed header. */
        uint64_t h = 0xcbf29ce484222325ull;
        for (size_t i = strtoul(argv[2], NULL, 0); i < RAM_BYTES; ++i)
            h = (h ^ ram[i]) * 0x100000001b3ull;
        printf("OK %u %016llx\n", thunk_count, (unsigned long long)h);
    } else printf("ERROR %s\n", stopped_reason);
    free(ram);
    return ok ? 0 : 2;
}
'''
    with tempfile.TemporaryDirectory(prefix='ngb-xbe-loader-') as tmp:
        tmp = Path(tmp)
        (tmp / 'loader.c').write_text(harness)
        subprocess.run(['cc', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(tmp / 'loader.c'), '-o', str(tmp / 'loader')], check=True)

        def check(name, data, error=None, same=None):
            path = tmp / (name + '.xbe')
            if data is not None:
                path.write_bytes(data)
            p = subprocess.run([str(tmp / 'loader'), str(path), str(base + headers)],
                               capture_output=True, text=True, timeout=20)
            assert p.returncode == (2 if error else 0), (name, p.stdout, p.stderr)
            assert not p.stderr, (name, p.stderr)
            if error:
                assert error in p.stdout, (name, p.stdout)
            elif same is not None:
                assert p.stdout == same, (name, p.stdout, same)
            print('PASS', name)
            return p.stdout

        reference = check('original', original)
        changed = bytearray(original)
        changed[4] ^= 1  # Signature; the game's mapped sections do not change.
        check('different-signature', changed, same=reference)
        changed = bytearray(original)
        certificate = u32(0x118) - base
        changed[certificate + 0x9c] ^= 1  # Allowed-media certificate flags.
        check('different-media-certificate', changed, same=reference)
        check('extra-file-padding', original + bytes(4096), same=reference)
        first = min(u32(table + i * 56 + 12) for i in range(count)
                    if u32(table + i * 56 + 16))
        changed = bytearray(original[:first] + bytes(4096) + original[first:])
        for i in range(count):
            offset = table + i * 56 + 12
            if u32(offset + 4):
                struct.pack_into('<I', changed, offset, u32(offset) + 4096)
        check('repacked-section-offsets', changed, same=reference)
        changed = bytearray(original)
        changed[first] ^= 1
        check('no-section-content-hash', changed)
        check('missing-file', None, 'Cannot open default.xbe')
        check('short-header', b'XBEH', 'Invalid or truncated')
        check('truncated-section', original[:headers], 'section')
        changed = bytearray(original)
        changed[0] ^= 1
        check('wrong-file-format', changed, 'header or section table')
        for name, offset, value, error in [
            ('invalid-entry', 0x128, 0, 'Unsupported XBE address layout'),
            ('oversized-header', 0x108, 0xffffffff, 'header or section table'),
            ('invalid-section-table', 0x120, 0, 'header or section table'),
            ('invalid-section-offset', table + 12, 0xffffffff, 'section'),
            ('invalid-section-address', table + 4, 0xffffffff, 'section'),
            ('invalid-import-address', 0x158, 0xffffffff ^ 0x5b6d40b6, 'kernel import address'),
        ]:
            changed = bytearray(original)
            struct.pack_into('<I', changed, offset, value)
            check(name, changed, error)


if __name__ == '__main__':
    main()
