"""Connect a private game caller to the private Xbox XDK implementation without
round-tripping through its large public entry wrapper. Mirror hooks must see
guest registers; always reload after them since a callback may change state."""
from pathlib import Path
import re, subprocess as sp,sys
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
scalar='--scalar' in sys.argv
p=NativeProbe('private-scalar' if scalar else 'private-d3d');p.driver((perf/'trial.inc').read_text());g=(REGS/'gates.s').read_text()
defs={n for f in REGS.glob('recomp_*.c.gated.s') for n in re.findall(r'^ngb_reg_d3d_orig_([0-9A-F]+):',f.read_text(),re.M)}
wrappers=(ROOT/'src/d3d/d3d_hooks.c').read_text();ids=dict(re.findall(r'(D3DF_\w+)\s*=\s*(\d+)',(ROOT/'src/d3d/d3d_funcs.h').read_text()))
sync='stp w19,w20,[x28]\n stp w21,w22,[x28,8]\n stp w23,w24,[x28,16]\n str w25,[x28,24]\n '
reload=sync.replace('stp','ldp').replace('str','ldr')
n=0
for va,fn in re.findall(r'void sub_([0-9A-F]+)\(void\)\s*/\* \w+ \*/\s*\{\s*if \(!d3d_hook\((D3DF_\w+)\)\) \{\s*d3d_orig_\1\(\);\s*d3d_after\(\2\);\s*\}\s*\}',wrappers):
 k='ngb_gate_sub_'+va+':\n'
 if k not in g or va not in defs:continue
 num=int(ids[fn]);n+=1
 g=g.replace(k,k+f''' adrp x16,trial_variant
 ldr w16,[x16,:lo12:trial_variant]
 cbz w16,1f
 stp x29,x30,[sp,-16]!
 mov x29,sp
 {sync}mov w0,#{num}
 bl d3d_hook
 {reload}cbnz w0,2f
 bl ngb_reg_d3d_orig_{va}
 {sync}mov w0,#{num}
 bl d3d_after
 {reload}2: ldp x29,x30,[sp],16
 ret
1:
''')
 if scalar and fn.removeprefix('D3DF_D3DDevice_') in ('SetTexture','SetStreamSource','LightEnable','SetRenderState_TextureFactor','SetRenderState_VertexBlend','SetVertexShaderConstant1','SetVertexShaderConstant4','SetRenderState_Simple'):
  # Leaf fast path accepts only normal memory. On fallback none of the
  # registers or renderer state has changed. On success private XDK
  # originals retain all entry/poll/guest-visible side effects.
  anchor=' mov x29,sp\n '+sync+'mov w0,#'+str(num)
  pos=g.index(anchor,g.index(k));prefix=f""" mov x29,sp
 mov w0,#{num}
 mov w1,w19
 mov w2,w20
 mov w3,w21
 mov w4,w22
 mov w5,w23
 bl scalar_mirror
 cbz w0,3f
 cmp w0,#2
 b.ne 4f
 mov w19,wzr
 add w22,w22,#4
 b 2f
4: mov w0,#{num}
 mov w1,#1
 bl scalar_track
 bl ngb_reg_d3d_orig_{va}
 mov w0,#{num}
 mov w1,#0
 bl scalar_track
 b 2f
3:"""
  g=g[:pos]+g[pos:].replace(' mov x29,sp',prefix,1)
if scalar:
 s=(ROOT/'src/d3d/hle.cpp').read_text()
 s+=(h/'scalar-mirror.inc').read_text()
 p.add('hle.cpp',s)
 hooks=(RUNTIME/'direct/hooks.c').read_text()+'\nvoid scalar_track(int fn,int entering){track_draw_call(fn,entering); }\n'
 o=p.compile('direct/hooks.c',hooks,['-include',str(RUNTIME/'switch_guest_regs.h')]);p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=o
assert n>30,n
f=p.out/'gates.S';f.write_text(g);o=p.out/'gates.o';sp.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(REGS/'gates.o'))]=str(o)
s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;';p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);ngb_trial_flip(scene_flips,draws);'));p.finish()
print('connected',n,'mirror wrappers')
