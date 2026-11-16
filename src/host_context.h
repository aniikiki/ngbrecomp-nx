/* Native context shared by XAPI fibers and cooperative Xbox threads.
 * Include the implementation in one translation unit per executable. */
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#if defined(__aarch64__)
/* AAPCS64: x19..x30, d8..d15, floating-point control and status. (Mach-O names start with an underscore.) */
#ifdef __APPLE__
#define CTX_SWITCH_SYM "_ngb_ctx_switch"
#define CTX_SWITCH_TYPE ""
#else
#define CTX_SWITCH_SYM "ngb_ctx_switch"
#define CTX_SWITCH_TYPE ".type ngb_ctx_switch,%function\n"
#endif
__asm__(
    ".text\n.p2align 2\n.globl " CTX_SWITCH_SYM "\n" CTX_SWITCH_TYPE CTX_SWITCH_SYM ":\n"
    "sub sp, sp, #176\n"
    "stp x19, x20, [sp, #0]\nstp x21, x22, [sp, #16]\n"
    "stp x23, x24, [sp, #32]\nstp x25, x26, [sp, #48]\n"
    "stp x27, x28, [sp, #64]\nstp x29, x30, [sp, #80]\n"
    "stp d8, d9, [sp, #96]\nstp d10, d11, [sp, #112]\n"
    "stp d12, d13, [sp, #128]\nstp d14, d15, [sp, #144]\n"
    "mrs x9, fpcr\nmrs x10, fpsr\nstp x9, x10, [sp, #160]\n"
    "mov x9, sp\nstr x9, [x0]\nmov sp, x1\n"
    "ldp x19, x20, [sp, #0]\nldp x21, x22, [sp, #16]\n"
    "ldp x23, x24, [sp, #32]\nldp x25, x26, [sp, #48]\n"
    "ldp x27, x28, [sp, #64]\nldp x29, x30, [sp, #80]\n"
    "ldp d8, d9, [sp, #96]\nldp d10, d11, [sp, #112]\n"
    "ldp d12, d13, [sp, #128]\nldp d14, d15, [sp, #144]\n"
    "ldp x9, x10, [sp, #160]\nmsr fpcr, x9\nmsr fpsr, x10\n"
    "add sp, sp, #176\nret\n");
void ngb_ctx_switch(void **save, void *load);
#elif !defined(_WIN32)
/* x86-64 SysV: save the callee-saved registers and the stack pointer, load
 * the other context's. A context that has never run starts in
 * fiber_host_entry via the return address planted below its stack top. */
__asm__(
    ".text\n"
    ".globl ngb_ctx_switch\n"
    ".type ngb_ctx_switch,@function\n"
    "ngb_ctx_switch:\n"            /* (void **save_sp, void *load_sp) */
    "  pushq %rbp\n"
    "  pushq %rbx\n"
    "  pushq %r12\n"
    "  pushq %r13\n"
    "  pushq %r14\n"
    "  pushq %r15\n"
    "  subq $8, %rsp\n"
    "  stmxcsr (%rsp)\n"
    "  fnstcw 4(%rsp)\n"
    "  movq %rsp, (%rdi)\n"
    "  movq %rsi, %rsp\n"
    "  ldmxcsr (%rsp)\n"
    "  fldcw 4(%rsp)\n"
    "  addq $8, %rsp\n"
    "  popq %r15\n"
    "  popq %r14\n"
    "  popq %r13\n"
    "  popq %r12\n"
    "  popq %rbx\n"
    "  popq %rbp\n"
    "  ret\n"
    ".size ngb_ctx_switch, .-ngb_ctx_switch\n");
void ngb_ctx_switch(void **save_sp, void *load_sp);
#endif

#ifndef _WIN32
static void *ngb_context_stack(void *stack, size_t size, void (*entry)(void))
{
    uint64_t *sp;
#ifdef __aarch64__
    sp = (uint64_t *)((char *)stack + size - 176);
    memset(sp, 0, 176);
    sp[11] = (uint64_t)(uintptr_t)entry;
#else
    sp = (uint64_t *)((char *)stack + size);
    *--sp = 0;                                  /* alignment / fake return */
    *--sp = (uint64_t)(uintptr_t)entry;  /* ngb_ctx_switch's ret */
    for (int i = 0; i < 6; i++)
        *--sp = 0;                              /* rbp rbx r12..r15 */
    *--sp = 0;                                  /* mxcsr + x87 cw slot */
    ((uint32_t *)sp)[0] = 0x1F80;               /* default MXCSR */
    ((uint16_t *)sp)[2] = 0x037F;               /* default x87 control */
#endif
    return sp;
}
#endif
