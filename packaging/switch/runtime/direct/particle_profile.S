/* These register-ABI entries bracket whole particle and draw-list passes. The
 * AAPCS callbacks preserve the guest registers in x19..x28. */
#include "../../../../src/d3d/native_cpu_phases.h"
.section .text.ngb_particle_profile,"ax",%progbits
.p2align 2
.macro profile_pass entry, kind
.global __wrap_\entry
.type __wrap_\entry,%function
__wrap_\entry:
    adrp x9, ngb_combat_enabled
    ldr w9, [x9, :lo12:ngb_combat_enabled]
    cbnz w9, 1f
    b __real_\entry
1:  stp x29, x30, [sp, #-32]!
    mov x29, sp
    mov w0, #\kind
    bl ngb_native_cpu_enter
    str w0, [sp, #16]
    bl __real_\entry
    ldr w0, [sp, #16]
    bl ngb_native_cpu_resume
    ldp x29, x30, [sp], #32
    ret
.size __wrap_\entry, .-__wrap_\entry
.endm
profile_pass ngb_reg_sub_00123D20, NGB_CPU_PARTICLE_UPDATE
profile_pass ngb_reg_sub_00123D50, NGB_CPU_PARTICLE_PREPARE
profile_pass ngb_reg_sub_00308CE0, NGB_CPU_ORDERED_LIST
.section .note.GNU-stack,"",%progbits
