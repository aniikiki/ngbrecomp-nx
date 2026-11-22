/* Test only the two menu callers, then dispatch through the same C guest
 * register file as the gameplay gates. Every other save uses the PGO body. */
.section .text.ngb_menu_profile,"ax",%progbits
.p2align 2
.global ngb_reg_sub_0030F9D0
.type ngb_reg_sub_0030F9D0,%function
ngb_reg_sub_0030F9D0:
    stp x29,x30,[sp,-16]!
    mov x29,sp
    stp w19,w20,[x28]
    stp w21,w22,[x28,8]
    stp w23,w24,[x28,16]
    str w25,[x28,24]
    bl ngb_is_menu_profile
    cbz w0,1f
    bl ngb_encode_menu_profile
    ldp w19,w20,[x28]
    ldp w21,w22,[x28,8]
    ldp w23,w24,[x28,16]
    ldr w25,[x28,24]
    ldp x29,x30,[sp],16
    ret
1:  ldp x29,x30,[sp],16
    b ngb_retail_profile_encoder
.size ngb_reg_sub_0030F9D0,.-ngb_reg_sub_0030F9D0
.section .note.GNU-stack,"",%progbits
