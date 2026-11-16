/* Private ABI entry: synchronize the guest register file only before callbacks.
 * Keep the three startup events and the poll predicate in sync with runtime.c. */
	.arch armv8-a
	.text
	.align	2
	.p2align 5,,15
	.global	ngb_reg_checkpoint
	.hidden	ngb_reg_checkpoint
	.type	ngb_reg_checkpoint, %function
ngb_reg_checkpoint:
.LFB0:
	.cfi_startproc
	stp	x29, x30, [sp, -16]!
	.cfi_def_cfa_offset 16
	.cfi_offset 29, -16
	.cfi_offset 30, -8
	adrp	x2, ngb_reg_entries
	mov	x29, sp
	ldr	x1, [x2, #:lo12:ngb_reg_entries]
	cmp	x1, 47
	bls	.L2
	mov	w3, 40976
	movk	w3, 0x17, lsl 16
	cmp	w0, w3
	mov	w3, 56400
	movk	w3, 0x31, lsl 16
	ccmp	w0, w3, 4, ne
	mov	w3, 49936
	movk	w3, 0x3c, lsl 16
	ccmp	w0, w3, 4, ne
	beq	.L2
	adrp	x3, ngb_reg_current_va
	str	w0, [x3, #:lo12:ngb_reg_current_va]
	add	x3, x1, 1
	and	x1, x1, 31
	str	x3, [x2, #:lo12:ngb_reg_entries]
	adrp	x2, ngb_reg_recent
	add	x2, x2, :lo12:ngb_reg_recent
	str	w0, [x2, x1, lsl 2]
	adrp	x1, ngb_guest_polls
	ldr	x0, [x1, #:lo12:ngb_guest_polls]
	add	x0, x0, 1
	str	x0, [x1, #:lo12:ngb_guest_polls]
	adrp	x1, ngb_poll_mask
	ldr	w1, [x1, #:lo12:ngb_poll_mask]
	tst	x1, x0
	beq	.L5
	adrp	x1, ngb_pending_dpcs
	ldr	w1, [x1, #:lo12:ngb_pending_dpcs]
	cbz	w1, .L1
.L5:
	stp w19, w20, [x28]
	stp w21, w22, [x28, 8]
	stp w23, w24, [x28, 16]
	str w25, [x28, 24]
	bl ngb_poll_due
	ldp w19, w20, [x28]
	ldp w21, w22, [x28, 8]
	ldp w23, w24, [x28, 16]
	ldr w25, [x28, 24]
.L1:
	ldp	x29, x30, [sp], 16
	.cfi_remember_state
	.cfi_restore 30
	.cfi_restore 29
	.cfi_def_cfa_offset 0
	ret
	.p2align 2,,3
.L2:
	.cfi_restore_state
	stp w19, w20, [x28]
	stp w21, w22, [x28, 8]
	stp w23, w24, [x28, 16]
	str w25, [x28, 24]
	bl ngb_checkpoint
	ldp w19, w20, [x28]
	ldp w21, w22, [x28, 8]
	ldp w23, w24, [x28, 16]
	ldr w25, [x28, 24]
	ldp	x29, x30, [sp], 16
	.cfi_restore 30
	.cfi_restore 29
	.cfi_def_cfa_offset 0
	ret
	.cfi_endproc
.LFE0:
	.size	ngb_reg_checkpoint, .-ngb_reg_checkpoint
.section .note.GNU-stack,"",%progbits
