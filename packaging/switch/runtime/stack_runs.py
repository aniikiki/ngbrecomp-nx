"""Combine ordinary RAM checks for consecutive x86 stack operations in hot game code."""
import re

# Game routines on the sampled Switch combat paths. Leave infrequent routines
# compact; each guarded sequence has a copy of its original slow path.
HOT = set("""
0030BCA0 003078B0 00307B80 001CB510 00148120 000298F0 00034E70 001CC5A0
00035A00 0013D330 0030C2A0 0030C240 000355B0 00035B90 0001FB60 00035940
00140AF0 001D7100 0013C050 001D6E20 00020040 001CBA70 001CC300 00149620
00307A10 001CB550 0003B1E0 001CB260 000E7D60 001CBBF0 00123D50 001249B0
00308BC0 001CBD00 0003B420 00038C70 001CBED0 0030B7E0 00317D10 001CA870
00151150 001CB9A0 00147DF0 000320E0 00149CB0
""".split())

REG = r"e(?:ax|bx|cx|dx|si|di|bp)"
VALUE = rf"(?:{REG}|0x[\da-fA-F]+u?|\d+)"
RUN = re.compile(rf"(?:^    PUSH32\(esp, {VALUE}\);(?:\n|(?= RECOMP_))){{3,}}"
                 rf"|(?:^    POP32\(esp, {REG}\);\n){{3,}}", re.M)
FUNCTION = re.compile(r"^void sub_([0-9A-F]{8})\(void\)\n\{.*?^\}", re.S | re.M)


def stack_run(match):
    original = match[0]
    operands = re.findall(r"32\(esp, (\w+)\);", original)
    push = original.lstrip().startswith("PUSH")
    size = 4 * len(operands)
    address = f"esp - {size}u" if push else "esp"
    lines = ["    {", f"        uint32_t first = {address};",
             f"        if (!(first & 3u) && (first & 4095u) + {size}u <= ngb_fast_page_bytes[first >> 12]) {{",
             "            volatile uint32_t *words = (volatile uint32_t *)(ngb_fast_ram + (first & 0x7fffffffu));"]
    for i, operand in enumerate(operands):
        if push:
            lines.append(f"            words[{len(operands)-1-i}] = {operand};")
        else:
            lines.append(f"            {operand} = words[{i}];")
    lines.extend(["            esp = first;" if push else f"            esp += {size}u;",
                  "        } else {", *["        " + line for line in original.rstrip().splitlines()],
                  "        }", "    }"])
    return "\n".join(lines) + "\n"


def combine_stack_runs(source):
    def change(m):
        return RUN.sub(stack_run, m[0]) if m[1] in HOT else m[0]
    return FUNCTION.sub(change, source)
