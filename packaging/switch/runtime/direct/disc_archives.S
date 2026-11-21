/* The retail archive loader registers the disc files itself. On a full
 * extracted disc the Xbox HDD installer has no work to do. Intercept its
 * producers before they touch instinfo.ins, evict files or schedule copies.
 * The sparse bootstrap disc still needs the original behavior.
 *
 * The lifted functions use the guest-register ABI: w19 is Xbox EAX and
 * w22 is Xbox ESP. Their bare RET consumes only the guest return address.
 * Polling functions return zero when there is no pending installation. */
.macro archive_entry address, poll=0
    .section .text.ngb_disc_\address,"ax",%progbits
    .p2align 2
    .global __wrap_ngb_reg_sub_\address
    .type __wrap_ngb_reg_sub_\address, %function
__wrap_ngb_reg_sub_\address:
    adrp x16, ngb_disc_archives_direct
    ldr w16, [x16, :lo12:ngb_disc_archives_direct]
    cbz w16, 1f
    .if \poll
        mov w19, wzr
    .endif
    add w22, w22, #4
    ret
1:  b __real_ngb_reg_sub_\address
    .size __wrap_ngb_reg_sub_\address, . - __wrap_ngb_reg_sub_\address
.endm

archive_entry 00302A30      /* read the install record and select cached demo */
archive_entry 00302B20, 1   /* poll startup demo installation */
archive_entry 00302BE0      /* register previously installed archives */
archive_entry 00302C90      /* evict cached archives at scene transitions */
archive_entry 00302CF0
archive_entry 00302D60, 1   /* poll foreground scene installations */
archive_entry 00302E20, 1
archive_entry 00302ED0, 1
archive_entry 00302F80, 1   /* schedule background installations during play */
archive_entry 003031B0, 1

.section .note.GNU-stack,"",%progbits
