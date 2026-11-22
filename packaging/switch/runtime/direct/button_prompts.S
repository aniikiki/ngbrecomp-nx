/* Retail SPR registration. The register build keeps Xbox ECX (the group)
 * in w20, the result in w19, and the guest RAM base in x26. */
.text
.p2align 2
.global ngb_reg_sub_0021AAC0
.type ngb_reg_sub_0021AAC0, %function
ngb_reg_sub_0021AAC0:
    mov w9, #0x2a40
    movk w9, #0x45, lsl #16
    cmp w20, w9                     /* base.spr */
    b.eq .Lprompt_group
    add w9, w9, #0x104              /* menu.spr and localized menus */
    cmp w20, w9
    b.ne .Lretail
.Lprompt_group:
    add x9, x26, w20, uxtw
    ldr w10, [x9, #0xc]
    cbnz w10, .Lretail              /* already registered */
    stp x9, x30, [sp, #-16]!
    bl ngb_retail_register_sprites
    ldp x0, x30, [sp], #16
    cbnz w19, .Ldone
    b ngb_switch_xy_prompts
.Ldone:
    ret
.Lretail:
    b ngb_retail_register_sprites
.size ngb_reg_sub_0021AAC0, .-ngb_reg_sub_0021AAC0
.section .note.GNU-stack,"",%progbits
