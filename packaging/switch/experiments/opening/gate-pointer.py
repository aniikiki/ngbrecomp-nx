"""Only one-byte guest pointer requests in the ordinary static image; preserve the full original slow gate."""
from pathlib import Path
import subprocess
def install(p,variant,high=False,census=False,ordinary=False):
    assert variant.name=='opening-full-page'
    s=(variant/'gates.s').read_text()
    k='\nngb_gate_ngb_guest_pointer:\n';assert s.count(k)==1
    low=''' cmp x1,#1
 b.ne 9f
 sub w9,w0,#8,lsl #12
 mov w10,#0xff0000
 orr w10,w10,#0x8000
 cmp w9,w10
 b.hs 9f
 cbz x26,9f
 add x0,x26,w0,uxtw
 ret
9:
'''
    fast=''' eor w9,w0,#0x80000000
 lsr w10,w9,#27
 cbnz w10,9f
 adrp x10,ngb_scene_active
 ldr w10,[x10,:lo12:ngb_scene_active]
 cbz w10,9f
 cbz x1,9f
 and w11,w9,#4095
 mov w12,#4096
 sub w12,w12,w11
 cmp x1,#1
 mov x13,#8
 csel x13,x13,x1,eq
 cmp x13,x12
 b.hi 9f
 lsr w9,w9,#12
 adrp x10,ngb_contiguous_pages
 add x10,x10,:lo12:ngb_contiguous_pages
 ldr x10,[x10,x9,lsl #3]
 cbz x10,9f
 adrp x12,ngb_target_pages
 add x12,x12,:lo12:ngb_target_pages
 ldrb w12,[x12,x9]
 cbnz w12,9f
 mov w13,#1
 adrp x12,ngb_vertex_dirty
 add x12,x12,:lo12:ngb_vertex_dirty
 strb w13,[x12,x9]
 adrp x12,ngb_texture_dirty
 add x12,x12,:lo12:ngb_texture_dirty
 strb w13,[x12,x9]
 add x0,x10,x11
 ret
9:
'''
    mapped=''' lsr w9,w0,#26
 cbnz w9,9f
 cbz x1,9f
 and w10,w0,#4095
 mov w11,#4096
 sub w11,w11,w10
 cmp x1,x11
 b.hi 9f
 lsr w9,w0,#12
 adrp x11,ngb_direct_pages
 add x11,x11,:lo12:ngb_direct_pages
 ldr x11,[x11,x9,lsl #3]
 cbz x11,9f
 add x0,x11,x10
 ret
9:
'''
    if census:
        assert high
        def count(offset):
            return f""" adrp x14,gate_enabled
 ldr w14,[x14,:lo12:gate_enabled]
 cbz w14,8f
 adrp x14,gate_counts
 add x14,x14,:lo12:gate_counts
 ldr w15,[x14,#{offset}]
 add w15,w15,#1
 str w15,[x14,#{offset}]
8:
"""
        fast=fast.replace(' ret\n9:\n',count(0)+' ret\n9:\n'+count(4))
    s=s.replace(k,k+(mapped if ordinary else fast if high else low))
    d=p.out/'gate-pointer.s';d.write_text(s)
    o=d.with_suffix('.o');subprocess.run(['cc','-c',d,'-o',o],check=True)
    p.link[p.link.index(str(variant/'gates.o'))]=str(o)
