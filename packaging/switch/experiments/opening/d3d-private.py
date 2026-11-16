"""Keep guest register ABI across D3D wrapper and original XDK body. The two
real HLE calls retain normal publication/reload around the call, including
scope timing, startup, after hooks and device-state updates."""
from pathlib import Path
import re,subprocess
def generate(root,regs,out):
 gates=(regs/'gates.s').read_text();public=(regs/'entry.S').read_text()
 funcs=(root/'src/d3d/d3d_funcs.h').read_text();wrap=(root/'src/d3d/d3d_hooks.c').read_text()
 ids={k:int(i) for k,i in re.findall(r'(D3DF_\w+) = (\d+)',funcs)}
 known=set(re.findall(r'^\.global d3d_orig_([0-9A-F]+)$',public,re.M))
 st='\tstp w19, w20, [x28]\n\tstp w21, w22, [x28, 8]\n\tstp w23, w24, [x28, 16]\n\tstr w25, [x28, 24]\n'
 ld=st.replace('stp','ldp').replace('str','ldr')
 n=0
 for va,fn in re.findall(r'void sub_([0-9A-F]+)\(void\)\s*/\* \w+ \*/\s*\{\s*if \(!d3d_hook\((D3DF_\w+)\)\) \{\s*d3d_orig_\1\(\);\s*d3d_after\(\2\);\s*\}\s*\}',wrap):
  if va not in known:continue
  key=f'ngb_gate_sub_{va}:\n';a=gates.find(key)
  if a<0:continue
  a+=len(key);b=gates.index(' ret\n',a)+5
  assert gates[a:b].count(' bl sub_'+va+'\n')==1
  impl=' stp x29,x30,[sp,-16]!\n mov x29,sp\n'+st+f' mov w0,#{ids[fn]}\n bl d3d_hook\n'+ld+f' cbnz w0,1f\n bl ngb_reg_d3d_orig_{va}\n'+st+f' mov w0,#{ids[fn]}\n bl d3d_after\n'+ld+'1:\n ldp x29,x30,[sp],16\n ret\n'
  gates=gates[:a]+impl+gates[b:];n+=1
 assert n>60,n
 print('canonical D3D gates changed:',n,flush=True);out.write_text(gates)
if __name__=='__main__':
 import sys
 root=Path.cwd();generate(root,root/'build/switch-runtime/native-regs',Path(sys.argv[1]))
