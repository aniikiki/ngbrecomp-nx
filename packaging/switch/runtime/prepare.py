#!/usr/bin/env python3
"""Instrument a separate, unmodified-game lift for fail-closed boot bring-up."""
from pathlib import Path
import hashlib
import shutil
import sys
import re
import struct

root = Path(__file__).resolve().parents[3]
raw = root / "build/switch-runtime/gen-raw"
out = root / "build/switch-runtime/gen"
if not (raw / "recomp_dispatch.c").is_file():
    raise SystemExit("Generate build/switch-runtime/gen-raw first")
out.mkdir(parents=True, exist_ok=True)
# Instrument in memory; unchanged outputs retain their mtime for incremental builds.
staged = {p.name: p.read_text() for p in raw.glob('*') if p.suffix in ('.c', '.h')}

types = out / "recomp_types.h"
s = staged[types.name]
needle = '#define XBOX_PTR(addr) ((uintptr_t)(uint32_t)(addr) + g_xbox_mem_offset)'
assert s.count(needle) == 1
s = s.replace(needle, '#include "guest_memory.h"\n#define XBOX_PTR(addr) ngb_guest_pointer((uint32_t)(addr), 1)')
for macro,ctype,size in [('MEM8','uint8_t',1),('MEM16','uint16_t',2),('MEM32','uint32_t',4),('MEM64','uint64_t',8),('SMEM8','int8_t',1),('SMEM16','int16_t',2),('SMEM32','int32_t',4),('SMEM64','int64_t',8),('MEMF','float',4),('MEMD','double',8)]:
    s = re.sub(r'^#define '+macro+r'\(addr\).*$', f'#define {macro}(addr) (*(volatile {ctype} *)ngb_guest_scalar((uint32_t)(addr), {size}))', s, flags=re.M)
# Keep the common XMM load/store inline. Out-of-line slow paths preserve
# target notifications and the four original accesses when crossing pages.
start = s.index("static inline RecompXmm XMM_MEM(")
end = s.index("/* movlps/movhps", start)
s = s[:start] + """static inline __attribute__((always_inline)) RecompXmm XMM_MEM(uint32_t addr) {
    RecompXmm r;
    if ((ngb_static_image_span(addr, 16) && ngb_fast_ram) ||
        __builtin_expect((addr & 4095u) + 16u <= ngb_fast_page_bytes[addr >> 12], 1))
        __builtin_memcpy(&r, ngb_fast_ram + (addr & 0x7fffffffu), sizeof(r));
    else
        ngb_vector_read_slow(addr, r.u);
    return r;
}

static inline __attribute__((always_inline)) void XMM_STORE(uint32_t addr, RecompXmm v) {
    if ((ngb_static_image_span(addr, 16) && ngb_fast_ram) ||
        __builtin_expect((addr & 4095u) + 16u <= ngb_fast_page_bytes[addr >> 12], 1))
        __builtin_memcpy(ngb_fast_ram + (addr & 0x7fffffffu), &v, sizeof(v));
    else
        ngb_vector_write_slow(addr, v.u);
}

""" + s[end:]
s = s.replace("memcpy(&r, (const void *)XBOX_PTR(addr), 8);", "memcpy(&r, (const void *)ngb_guest_scalar(addr, 8), 8);")
s = s.replace("memcpy((void *)XBOX_PTR(addr), &v, 8);", "memcpy((void *)ngb_guest_scalar(addr, 8), &v, 8);")
# Override only the staged template. PC/Android generation remains untouched.
s += '''
#undef RECOMP_ENTRY
#define RECOMP_ENTRY(va) ngb_checkpoint(va)
#undef __debugbreak
#define __debugbreak() ngb_stop("guest debug break", 0)
'''
staged[types.name] = s

stubs = out / "recomp_stubs_unresolved.c"
text = staged[stubs.name]
text, count = re.subn(r'void (sub_([0-9A-Fa-f]{8}))\(void\) \{[^\n]*\}',
    lambda m: f'void {m[1]}(void) {{ ngb_stop("unresolved generated target", 0x{m[2]}u); }}', text)
assert count > 0
staged[stubs.name] = text

# The Switch runner calls through the immutable lifted function table. A
# compact index avoids doing a binary search for each guest indirect call
# and does not need an allocation spanning every byte of the XBE.
dispatch = staged["recomp_dispatch.c"]
targets = [int(key, 16) for key in re.findall(
    r"^    \{ 0x([0-9A-Fa-f]+)u, \(recomp_func_t\)", dispatch, re.M)]
assert len(targets) == int(re.search(r"g_recomp_table_size = (\d+);", dispatch)[1])
assert len(set(targets)) == len(targets) < 65535
bits = (len(targets) * 2 - 1).bit_length()
slots = [0] * (1 << bits)
for index, key in enumerate(targets, 1):
    slot = ((key * 0x9e3779b1) & 0xffffffff) >> (32 - bits)
    while slots[slot]:
        slot = (slot + 1) % len(slots)
    slots[slot] = index
initializer = ",\n".join("    " + ", ".join(map(str, slots[i:i+16])) for i in range(0, len(slots), 16))
start = dispatch.index("static recomp_func_t *g_flat_table")
end = dispatch.index("/* Get the number of registered functions */", start)
staged["recomp_dispatch.c"] = dispatch[:start] + f"""static const uint16_t dispatch_index[] = {{
{initializer}
}};

int recomp_dispatch_init(void) {{ return 1; }}
size_t recomp_dispatch_flat_bytes(void) {{ return sizeof(dispatch_index); }}

recomp_func_t recomp_lookup(uint32_t xbox_va)
{{
    if (xbox_va - g_flat_base >= g_flat_span) return NULL;
    unsigned slot = (xbox_va * 0x9e3779b1u) >> {32 - bits};
    while (dispatch_index[slot]) {{
        unsigned index = dispatch_index[slot] - 1;
        if (g_recomp_table[index].xbox_va == xbox_va) return g_recomp_table[index].func;
        slot = (slot + 1) & {len(slots) - 1};
    }}
    return NULL;
}}

""" + dispatch[end:]

# Split loads and stores in the USB and NV2A bootstrap routines.
# Other routines keep rejecting unmapped MMIO until their device is wired.
mmio_startup = {'003DA509', '003DA514', '003D9F5D', '003DA4A8', '003DF9CE',
               '003D9E5F', '003DFE3D', '003E0511', '003DE3F0', '003DFEF7',
                '003DFA0B', '003DE35B', '003DE3A8', '003E0D4D',
                '003CA920', '003CF055', '003CF080', '003CF980', '003CF0C3', '003D2C43', '003D2DA6',
                '003D2EA6', '003D2F75', '003D2FAB', '003D2FDB', '003CF144',
                '003D304C', '003D32C8', '003D3307', '003D3461', '003D34E6', '003D36DE',
                '003CD040', '003CACD0', '003CAE80', '003CF7E7', '003CF53F', '003CFAA0', '003CFEB0', '003D3428', '003CFC50', '003CFB80', '003D0408', '003D0100', '003CA9A0', '003D0486'}
# All routines in the XBE's OHCI transfer and completion driver can touch
# mapped device registers through pointers (including pointers on the stack).
for unit in staged.values():
    mmio_startup.update(a for a in re.findall(r'^void sub_([0-9A-F]{8})\(void\)\n\{', unit, re.M)
                        if '003DE000' <= a <= '003E1269' or '0037A6C0' <= a < '00396EC0')
# The audio library uses both signed decimal and hex literals for MCPX.
# Instrument statically known audio registers without changing normal RAM.
audio_addr = re.compile(r'MEM32\((-?\d+|0x[0-9a-fA-F]+)u?\)')
for unit, body in list(staged.items()):
    if not unit.endswith('.c'):
        continue
    audio_operands = {m[0]: m[1] for m in audio_addr.finditer(body)
                      if 0xfe800000 <= (int(m[1],0) & 0xffffffff) < 0xfe880000}
    # Some guest tests only examine the low byte of the control word.
    for m in list(re.finditer(r'MEM8\((-?\d+|0x[0-9a-fA-F]+)u?\)', body)):
        addr = int(m[1],0) & 0xffffffff
        if 0xfe800000 <= addr < 0xfe880000:
            assert m[0] + ' = ' not in body
            body = body.replace(m[0], f'((uint8_t)(ngb_bus_read32(0x{addr&~3:x}u) >> {(addr&3)*8}))')
    # Substitute each codec access at its original width, including channel
    # offsets computed in a register. Codec reset bits have write semantics.
    ac = r'\bMEM(8|16|32)\(([^()\n]*?(-2097\d{4}|0xFEC00[0-9A-F]{3})u?)\)'
    def codec_access(m):
        if not 0xfec00000 <= (int(m[3], 0) & 0xffffffff) < 0xfec01000:
            return m[0]
        width = int(m[1]) // 8
        if m.lastindex == 4:
            return f'    ngb_ac97_write({m[2]}, {width}, {m[4]});'
        return f'ngb_ac97_read({m[2]}, {width})'
    body = re.sub(r'^    ' + ac + r' = ([^;\n]+);', codec_access, body, flags=re.M)
    body = re.sub(ac, codec_access, body)
    if audio_operands or body != staged[unit]:
        for operand, address in audio_operands.items():
            body = re.sub(r'^    ' + re.escape(operand) + r' = ([^;\n]+);',
                          lambda m: '    ngb_bus_write32(' + address + ', ' + m[1] + ');',body,flags=re.M)
            body = body.replace(operand, 'ngb_bus_read32(' + address + ')')
        staged[unit] = '#include "ohci_boot.h"\n' + body
wired = set()

def instrument_mmio(match):
    address, body = match.group(1), match.group(0)
    if address not in mmio_startup:
        return body
    wired.add(address)
    if address == '003D0486':
        body = re.sub(r'^    MEM8\((ecx \+ 0x6813C[89])\) = (.*?);',
                      r'    ngb_nv2a_write8(\1, \2);', body, flags=re.M)
    if address == '003CFC50':
        body = body.replace('MEM8(edi + 0x6013D4) = LO8(ebx);', 'ngb_nv2a_write8(edi + 0x6013D4, LO8(ebx));')
        body = body.replace('MEM8(edi + 0x6013D4)', 'ngb_nv2a_read8(edi + 0x6013D4)')
    if address == '003CFAA0':
        body = body.replace('MEM8(eax + 0x8100)', '(uint8_t)ngb_bus_read32(eax + 0x8100)')
    if address == '003CF7E7':
        # This idle-wait routine polls only the low byte of FIFO status words.
        body = body.replace('MEM8(', 'ngb_nv2a_read8(')
    if address == '003D2EA6':
        # The CRTC index/data ports are byte-wide. All byte accesses here
        # use one of the two ports; the routine also touches ordinary RAM.
        body = re.sub(r'^    MEM8\((eax \+ 0x6013D[45])\) = (.*?);',
                      r'    ngb_nv2a_write8(\1, \2);', body, flags=re.M)
        body = body.replace('MEM8(eax + 0x6013D5)', 'ngb_nv2a_read8(eax + 0x6013D5)')
    if address == '003D2C43':
        # This guest clock probe reads the N coefficient as a byte on all three PLLs.
        body, count = re.subn(r'ZX8\(MEM8\(eax \+ 1\)\)', 'ngb_nv2a_read8(eax + 1)', body)
        assert count == 3
    body = re.sub(r'^    MEM32\(([^()\n]+)\) = ([^;\n]+);',
                  r'    ngb_bus_write32(\1, \2);', body, flags=re.M)
    # REP STOS writes ordinary RAM through the bounded guest pointer.
    body = '\n'.join(line if 'for (_i' in line else re.sub(r'\bMEM32\(', 'ngb_bus_read32(', line)
                     for line in body.split('\n'))
    return body

for unit, body in list(staged.items()):
    if unit.endswith('.c') and any('void sub_' + a + '(void)\n{' in body for a in mmio_startup):
        headers = '#include "ohci_boot.h"\n'
        if 'void sub_003D2C43(void)\n{' in body:
            headers += '#include "nv2a_boot.h"\n'
        staged[unit] = headers + re.sub(
            r'void sub_([0-9A-F]{8})\(void\)\n\{.*?^\}', instrument_mmio, body, flags=re.M | re.S)
assert wired == mmio_startup

# XAPI SwitchToFiber must switch both the emulated stack and the C call chain.
for unit, body in staged.items():
    if 'void sub_0032A293(void)\n{' in body:
        staged[unit], n = re.subn(r'void sub_0032A293\(void\)\n\{.*?^\}',
            'void sub_0032A293(void) { extern void ngb_switch_fiber(void); ngb_switch_fiber(); }',
            body, count=1, flags=re.M | re.S)
        assert n == 1

# Vectorize the two copies of the XDK matrix product only when both inputs
# are on ordinary mapped pages. Retain each guest epilogue and its stores.
matrix_functions = {"00328232", "003CC550"}
for unit, body in staged.items():
    for address in matrix_functions:
        marker = f"void sub_{address}(void)\n{{"
        if marker not in body:
            continue
        start = body.index(marker)
        end = body.index("\n}", start)
        fn = body[start:end]
        first_load = "    xmm2 = XMM_MEM(eax);"
        first_store = "    XMM_STORE(ecx, xmm2);"
        assert fn.count(" = XMM_MUL(") == 16 and fn.count(" = XMM_ADD(") == 12
        assert fn.count(first_load) == fn.count(first_store) == 1
        fn = fn.replace(first_load, """    if (ngb_matrix_product(eax, ecx)) {
        ecx = MEM32(esp + 4);
        goto store_product;
    }
""" + first_load).replace(first_store, "store_product:\n" + first_store)
        body = body[:start] + fn + body[end:]
        pos = body.index('#include "recomp_funcs.h"') + len('#include "recomp_funcs.h"')
        staged[unit] = body[:pos] + '\n#include "matrix.h"' + body[pos:]

# NGB's texture-stage setter compares eight consecutive material words with
# its own cached copy. When all match, the original path performs no writes,
# calls, or conditional poll. Rejoin where ECX and the compare flags are
# overwritten. Keep the original path for any changed or special-memory word.
for unit, body in staged.items():
    start = body.find("loc_0030BA4E: ;")
    if start < 0:
        continue
    end = body.index("loc_0030BB81: ;", start)
    block = body[start:end]
    assert block.count(" = ecx;") == 16 and block.count(" = ebx;") == 8
    marker = "    edx = 0x800;"
    assert block.count(marker) == 1 and block.count("PUSH32(esp, ebx)") == 1
    staged[unit] = body[:start] + block.replace(marker, marker + """
    if (CMP_EQ(_fa, _fb)) {
        const void *material = ngb_ram_span(edi + 0x14, 28);
        const void *cached = ngb_ram_span(eax + 0x9779AC, 28);
        if (material && cached && __builtin_memcmp(material, cached, 28) == 0)
            goto loc_0030BB81;
    }""") + body[end:]

# Replace only the arithmetic in three sampled game routines. The original
# stores, register epilogues, guest polls and special-memory paths stay active.
for unit, body in list(staged.items()):
    original = body
    for address, translate, stack_offset in (("00140AF0", True, "0x14"), ("003066B0", False, "8")):
        marker = f"void sub_{address}(void)\n{{"
        if marker not in body:
            continue
        start = body.index(marker)
        end = body.index("\n}", start)
        fn = body[start:end]
        first = fn.index("    xmm2 = XMM_SCALAR(MEMF(eax));")
        last = fn.index("\n", fn.index("    xmm2 = XMM_ADD(xmm2, xmm3);", first))
        block = fn[first:last]
        assert block.count("XMM_MUL(") == 3 and block.count("XMM_ADD(") == 2 + translate
        flag = "true" if translate else "false"
        native = (f"#ifdef __aarch64__\n    if (ngb_arm_transform(eax, 0x950180, {flag})) {{\n"
                  f"        ecx = 0x950180;\n        eax = MEM32(esp + {stack_offset});\n"
                  "    } else\n#endif\n    {\n" + block + "\n    }")
        body = body[:start] + fn[:first] + native + fn[last:] + body[end:]
    for label, base, initial, column, done in (
            ("0037A600", "ecx", "0xFFFFFFF0u", "true", "0037A62B"),
            ("0037A667", "edx", "0xFFFFFFFCu", "false", "0037A690")):
        marker = f"loc_{label}: ;"
        if marker not in body:
            continue
        first = body.index("    { double _t", body.index(marker))
        last = body.index("/* fstp */", first)
        assert body[first:last].count("/* fmul") == 4 and body[first:last].count("/* faddp") == 3
        native = (f"#ifdef __aarch64__\n    if (esi == {initial} && ngb_arm_x87_row({base}, ebx, {column})) {{\n"
                  f"        esi = 0;\n        goto loc_{done};\n    }}\n#endif\n")
        body = body[:first] + native + body[first:]
    if body != original:
        marker = '#include "recomp_funcs.h"'
        assert body.count(marker) == 1
        staged[unit] = body.replace(marker, marker + '\n#ifdef __aarch64__\n#include "arm_math.h"\n#endif')

# Log a prolonged poll from the title's buffer teardown with its actual
# returned status. The counter belongs to this invocation and buffer.
for unit, body in staged.items():
    if "loc_0032094C: ;" not in body:
        continue
    assert body.count("loc_00320920: ;") == body.count("loc_0032094C: ;") == 1
    body = body.replace("void sub_00320900(void)\n{", "void sub_00320900(void)\n{\n    unsigned status_polls;")
    body = body.replace("loc_00320920: ;", "loc_00320920: ;\n    status_polls = 0;")
    body = body.replace("loc_0032094C: ;", """loc_0032094C: ;
    if (++status_polls == 16384 && (MEM32(esi) & 1)) {
        char line[112];
        snprintf(line, sizeof(line), "DirectSound stop pending caller=0032094c buffer=%08x status=%08x",
                 MEM32(esi - 64), MEM32(esi));
        ngb_kernel_log(line);
    }""")
    staged[unit] = body

# The XDK copies eight quadwords at a time while writing an indexed draw.
# Translate each ordinary page once, preserving its original register loads,
# stores, and loop poll. Cross-page and special accesses keep the original path.
for unit, body in staged.items():
    marker = "loc_003C9CC0: ;"
    if marker not in body:
        continue
    start = body.index("    mm0 = MMX_MEM(esi);", body.index(marker))
    end = body.index(" /* movntq */", body.index("    MMX_STORE(edi + 0x38, mm7);", start)) + len(" /* movntq */")
    block = body[start:end]
    assert block.count("MMX_MEM") == block.count("MMX_STORE") == 8
    loads = [f"            memcpy(&mm{i}, source + {8*i}, 8);" for i in range(8)]
    stores = [f"            memcpy(dest + {8*i}, &mm{i}, 8);" for i in range(8)]
    fast = ["    {", "        const unsigned char *source = (esi & 4095) <= 4096-64 ? ngb_guest_vector_page(esi) : NULL;",
            "        unsigned char *dest = (edi & 4095) <= 4096-64 ? ngb_guest_vector_page(edi) : NULL;",
            "        if (source && dest) {", *loads, *stores, "        } else {", block, "        }", "    }"]
    staged[unit] = body[:start] + "\n".join(fast) + body[end:]

# 5849 DrawIndexedVertices has already flushed state and reserved ring space at
# 9BAB. For an immediate strip captured by the native renderer, leave BEGIN/END
# in the ring and rejoin the original resource/fence epilogue. Recording a
# reusable Xbox push buffer (device flag 4) still needs the actual index words.
for unit, body in staged.items():
    if "loc_003C9BAB: ;" not in body:
        continue
    anchor = "    MEM32(eax + 4) = ecx;\n    eax = ebx;"
    pos = body.index(anchor, body.index("loc_003C9BAB: ;"))
    assert pos < body.index("loc_003C9BD7: ;") and body.count("loc_003C9DDA: ;") == 1
    prefix = """    MEM32(eax + 4) = ecx;
#ifdef NGB_DIRECT3D
    extern int ngb_direct_compact_indices(uint32_t stack, uint32_t count);
    if (!(MEM8(MEM32(ebp - 8) + 8) & 4) &&
        ngb_direct_compact_indices(ebp + 4, edx)) goto loc_003C9DDA;
#endif
    eax = ebx;"""
    body = body[:pos] + body[pos:].replace(anchor, prefix, 1)
    entry = "    RECOMP_ENTRY(0x003C9B40u);"
    assert body.count(entry) == 1
    body = body.replace(entry, entry + """
#ifdef NGB_DIRECT3D
    uint64_t reference_start = 0;
    if (ngb_direct_try_indexed(&reference_start)) return;
#endif""")
    tail = body.index("loc_003C9E0B: ;")
    ret = "    esp += 16; return; /* ret 12 */"
    assert ret in body[tail:body.index("\n}", tail)]
    body = body[:tail] + body[tail:].replace(ret, """    esp += 16;
#ifdef NGB_DIRECT3D
    if (reference_start) ngb_direct_index_reference_done(reference_start);
#endif
    return; /* ret 12 */""", 1)
    staged[unit] = '#ifdef NGB_DIRECT3D\n#include "direct/output.h"\n#endif\n' + body

# Log the return to the game at both CreateDevice call sites, including HRESULT.
for unit in staged:
    if unit.endswith('.c'):
        staged[unit] = staged[unit].replace('RECOMP_ABI_CALL(0x003CC310u, sub_003CC310);',
            'RECOMP_ABI_CALL(0x003CC310u, sub_003CC310); ngb_device_return(eax);')

# REP MOVS can have a null source when its count is zero (this XBE has an
# empty TLS template). Check the whole transfer, and allow empty ranges.
blocks = transfers = 0
for name in [name for name in staged if name.endswith('.c')]:
    s = staged[name]
    s, n = re.subn(r'uint8_t \*_d = \(uint8_t\*\)XBOX_PTR\(edi\), \*_s = \(uint8_t\*\)XBOX_PTR\(esi\); uint32_t _n = ([^;]+);',
        r'uint32_t _n = \1; uint8_t *_d = (uint8_t*)ngb_guest_pointer(edi, _n), *_s = (uint8_t*)ngb_guest_pointer(esi, _n);', s)
    transfers += n
    s = s.replace('memset((void*)XBOX_PTR(edi), (uint8_t)eax, ecx)',
                  'memset((void*)ngb_guest_pointer(edi, ecx), (uint8_t)eax, ecx)')
    # Every cycle has a backward edge in the emitted C. Poll there and at
    # guest function entry (ngb_checkpoint). Periodic checkpoints also
    # cover long straight-line portions without duplicating the IRQ path
    # at every forward branch. Blocking kernel waits still poll directly.
    labels = list(re.finditer(r'^(loc_[0-9A-Fa-f]+): ;$', s, re.M))
    # Overlapping lifts can repeat a guest label in different C functions.
    # Its earliest definition includes every backedge to either copy.
    positions = {}
    for label in labels:
        positions.setdefault(label[1], label.start())
    checkpoints = {m[1] for m in re.finditer(r'\bgoto (loc_[0-9A-Fa-f]+);', s)
                   if m[1] in positions and positions[m[1]] <= m.start()}
    checkpoints.update(m[1] for m in labels[::32])
    n = len(checkpoints)
    s = re.sub(r'^(loc_[0-9A-Fa-f]+): ;$', lambda m:
               m[0] + (' ngb_guest_block_poll();' if m[1] in checkpoints else ''), s, flags=re.M)
    if 'void sub_0031D570(void)\n{' in s:
        start = 'ecx = MEM32(ebp + 0x10);'
        pos = s.index(start, s.index('void sub_0031D570(void)\n{')) + len(start)
        s = s[:pos] + ' ngb_select_movie(ecx);' + s[pos:]
        status = 'loc_0031DA70: ;'
        assert s.count(status) == 1
        s = s.replace(status, status + ' eax = ngb_movie_status(eax);')
    blocks += n
    staged[name] = s
assert transfers and blocks

# Replace the straight-line parts, after the original reservation and polls.
# Allocation, binding lifetimes and uncommon inputs keep the XDK path.
for unit, body in staged.items():
    if 'loc_003C763B: ;' not in body:
        continue
    include = '#include "recomp_funcs.h"'
    assert body.count(include) == 1
    body = body.replace(include, include + '\n#ifdef NGB_DIRECT3D\n#include "direct/material.h"\n#endif')
    start = body.index('    fp_push(MEMF(ebx + 0x40));', body.index('loc_003C763B: ;'))
    end = body.index('    eax = MEM32(ebx);', start)
    assert 'ngb_guest_block_poll' not in body[start:end] and 'goto ' not in body[start:end]
    body = (body[:start] + '#ifdef NGB_DIRECT3D\n    if (!ngb_normalize_light())\n#endif\n    {\n' +
            body[start:end] + '    }\n' + body[end:])
    start = body.index('    ecx = MEM32(ebp + 0xC);', body.index('loc_003C7A5C: ;'))
    end = body.index('loc_003C7ACA: ;', start)
    assert 'ngb_guest_block_poll' not in body[start:end]
    body = (body[:start] + '#ifdef NGB_DIRECT3D\n    if (ngb_write_texture_packet(ebp, esi)) goto loc_003C7ACA;\n#endif\n' + body[start:])
    start = body.index('    esi = eax + eax * 2;', body.index('loc_003C8726: ;'))
    end = body.index('loc_003C8775: ;', start)
    assert 'ngb_guest_block_poll' not in body[start:end]
    body = body[:start] + """#ifdef NGB_DIRECT3D
    switch (ngb_bind_stream(ebp)) {
    case 1: goto loc_003C8775;
    case 2: goto loc_003C8782;
    }
#endif
""" + body[start:]
    for label, registers in [('003C91B1', 1), ('003C9214', 4)]:
        start = body.index('    MEM32(0x3D5F20) = eax;', body.index('loc_' + label + ': ;'))
        end = body.index('    POP32(esp, ebx);' if registers == 1 else '    esp += 4; return;', start)
        assert 'ngb_guest_block_poll' not in body[start:end]
        body = (body[:start] + f'#ifdef NGB_DIRECT3D\n    if (!ngb_write_constants({registers}))\n#endif\n    {{\n' +
                body[start:end] + '    }\n' + body[end:])
    staged[unit] = body


image = (root / "game_files/default.xbe").read_bytes()
image_sha = hashlib.sha256(image).hexdigest()
if len(image) != 4571136 or image[:4] != b'XBEH' or (
        struct.unpack_from('<I', image, 0x128)[0] ^ 0xa8fc57ab) != 0x0032b385:
    raise SystemExit('This bootstrap requires the supported NGB XBE layout')
fingerprint = raw / 'input.sha256'
if not fingerprint.exists() or fingerprint.read_text().strip() != image_sha:
    raise SystemExit('Generated code/image mismatch; run bash packaging/switch/build-runtime.sh host --generate')
fnv = 0xcbf29ce484222325
for b in image:
    fnv = ((fnv ^ b) * 0x100000001b3) & 0xffffffffffffffff
sys.path.insert(0, str(root / "xboxrecomp"))
from tools.xbe_parser.xbe_parser import KERNEL_EXPORTS
header = ['#pragma once', f'#define NGB_IMAGE_BYTES {len(image)}u',
          f'#define NGB_IMAGE_FNV 0x{fnv:016x}ull',
          f'#define NGB_IMAGE_SHA256 "{image_sha}"',
          'static const char *ngb_kernel_name(unsigned ordinal) { switch (ordinal) {']
header += [f'case {ordinal}: return "{name}";' for ordinal,name in sorted(KERNEL_EXPORTS.items())]
header += ['default: return "unknown kernel ordinal"; } }']
staged['ngb_image.h'] = '\n'.join(header)+'\n'
# Keep both the stock body and public entry available to the Direct3D hooks.
hooks = (root / "src/d3d/d3d_hooks.c").read_text()
entries = set(re.findall(r"void d3d_orig_([0-9A-F]+)\(void\);", hooks))
wrapped = set()
direct_units = []
def wrap_d3d(m):
    if m[1] not in entries:
        return m[0]
    wrapped.add(m[1])
    return f"#ifdef NGB_DIRECT3D\nvoid d3d_orig_{m[1]}(void)\n#else\nvoid sub_{m[1]}(void)\n#endif\n{{"
for unit in list(staged):
    if unit.endswith(".c"):
        text = re.sub(r"^void sub_([0-9A-F]+)\(void\)\n\{", wrap_d3d, staged[unit], flags=re.M)
        if text != staged[unit]:
            staged[unit] = text
            direct_units.append(unit)
# The mesh submitter has a single normal return; keep scope timing outside
# the generated arithmetic. Both entry and exit run on the guest thread.
mesh_units = [unit for unit, body in staged.items() if "loc_0030BCA0: ;" in body]
assert len(mesh_units) == 1
unit, = mesh_units
body = staged[unit]
begin = body.index("    RECOMP_ENTRY(0x0030BCA0u);")
end = body.index("\n}", begin)
mesh = body[begin:end]
assert mesh.count("return;") == 1
mesh = mesh.replace("    RECOMP_ENTRY", "#ifdef NGB_DIRECT3D\n    ngb_direct_mesh_scope(1);\n#endif\n    RECOMP_ENTRY", 1)
mesh = mesh.replace("    esp += 4; return;", "#ifdef NGB_DIRECT3D\n    ngb_direct_mesh_scope(0);\n#endif\n    esp += 4; return;")
staged[unit] = '#ifdef NGB_DIRECT3D\n#include "direct/output.h"\n#endif\n' + body[:begin] + mesh + body[end:]
if unit not in direct_units:
    direct_units.append(unit)
# Insert after poll placement so the ordinary path retains the game's exact
# interruption points and the scan can stop before the next pending poll.
for address, fragment in (("00308BF0", "tree_insert.inc"), ("00149D40", "scan_tags.inc")):
    label = f"loc_{address}: ;"
    units = [name for name, text in staged.items() if label in text]
    assert len(units) == 1
    name, = units
    assert staged[name].count(label) == 1
    staged[name] = staged[name].replace(label, label + f'\n#include "{fragment}"\n')
from stack_runs import combine_stack_runs
for name in staged:
    if name.endswith(".c"):
        staged[name] = combine_stack_runs(staged[name])
assert wrapped == entries, entries - wrapped
staged["direct_units.cmake"] = "set(NGB_DIRECT_UNITS " + " ".join(sorted(direct_units)) + ")\n"
for name, content in staged.items():
    p = out / name
    if not p.exists() or p.read_text() != content:
        p.write_text(content)
print(f"Staged {len(list(out.glob('*.c')))} C files; {count} unresolved targets fail closed")
