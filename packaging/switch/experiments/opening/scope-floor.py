"""Diagnostic only: remove draw/mesh/material attribution, keeping game work and frame clocks."""
from pathlib import Path
import subprocess
def hooks(s):
    def body(src,name,replacement):
        k=name+'\n{';assert src.count(k)==1,name
        a=src.index(k)+len(k);b=src.index('\n}',a)
        return src[:a]+'\n    '+replacement+src[b:]
    for name in ['static void track_draw_call(int fn, int entering)','void ngb_direct_mesh_scope(int enter)','static void publish_scope(void)','static void charge_scope(void)','void ngb_direct_timing_flip(unsigned completed)']:
        s=body(s,name,'/* Attribution disabled in this diagnostic. */')
    k='    ngb_direct_detail_frame = 1;\n    index_time.edge = ngb_elapsed_ns();'
    assert s.count(k)==1;s=s.replace(k,'    ngb_direct_detail_frame = 0;')
    return s
def hle(s):
    k='bool measure = ngb_direct_detail_frame != 0;'
    assert s.count(k)==1
    return s.replace(k,'constexpr bool measure = false;')
def gate(p,variant):
    s=(variant/'gates.s').read_text()
    k='ngb_gate_ngb_direct_mesh_scope:\n';assert s.count(k)==1
    a=s.index(k)+len(k);b=s.index('.size ngb_gate_ngb_direct_mesh_scope,',a)
    assert ' bl ngb_direct_mesh_scope\n' in s[a:b]
    f=p.out/'scope-floor.s';o=f.with_suffix('.o');f.write_text(s[:a]+' ret\n'+s[b:])
    subprocess.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(variant/'gates.o'))]=str(o)
