 adrp x9,gp_on
 ldr w9,[x9,:lo12:gp_on]
 cbz w9,.Lgp_done
 eor x9,x30,x16,ror #17
 eor x9,x9,x9,lsr #23
 ubfx x9,x9,#2,#13
 adrp x10,gp_rows
 add x10,x10,:lo12:gp_rows
 mov w14,#8192
.Lgp_find:
 add x11,x10,x9,lsl #5
 ldp x12,x13,[x11]
 cbz x12,.Lgp_new
 cmp x12,x30
 ccmp x13,x16,#0,eq
 b.eq .Lgp_count
 add x9,x9,#1
 and x9,x9,#8191
 subs w14,w14,#1
 b.ne .Lgp_find
 brk #0
.Lgp_new:
 stp x30,x16,[x11]
.Lgp_count:
 ldr x12,[x11,#16]
 add x12,x12,#1
 str x12,[x11,#16]
.Lgp_done:
