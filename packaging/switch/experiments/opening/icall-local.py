"""Resolve five strong runtime data symbols directly in guest code; keep PIC and all trace writes."""
from pathlib import Path
import runpy
p=Path(__file__).parent
header=Path('build/switch-runtime/gen/recomp_types.h').read_text()
decls=['uint32_t g_xbox_code_lo','uint32_t g_xbox_code_hi',
       'volatile uint32_t g_icall_trace[ICALL_TRACE_SIZE]',
       'volatile uint32_t g_icall_trace_idx','volatile uint64_t g_icall_count']
def transform(s,unit):
    for decl in decls:assert 'extern '+decl+';' in header
    return '#include <stdint.h>\n'+''.join('extern __attribute__((visibility("hidden"))) '+decl.replace('[ICALL_TRACE_SIZE]','[]')+';\n' for decl in decls)+s
runpy.run_path(str(p/'model-copy.py'))['build']('icall-local',[(True,[2,10,16,26,39]),(False,[28])],transform)
