from pathlib import Path
import os,re,subprocess as sp,concurrent.futures as cf
old=Path(os.environ.get('NGB_REG_OUT','/work/build/switch-runtime/native-regs'));out=old
cc='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc'
store='\tstp w19, w20, [x28]\n\tstp w21, w22, [x28, 8]\n\tstp w23, w24, [x28, 16]\n\tstr w25, [x28, 24]\n';load=store.replace('stp','ldp').replace('str','ldr')
targets=set()
def build(obj):
 s=obj.read_text()
 local=set(re.findall(r'^\s*\.type\s+([\w.]+), %function',s,re.M))
 def sub(m):
  op,t=m.groups()
  if op=='blr':
   # The indirect ABI calls in the generated header invoke void(void) only.
   return '\tmov x16,'+t+'\n\tbl ngb_gate_indirect\n'
  if t=='ngb_checkpoint':return '\tbl ngb_reg_checkpoint\n'
  if t in local:return '\tbl '+t+'\n'
  if re.fullmatch(r'(?:sub_|d3d_orig_)[0-9A-F]+',t) or t in {
    'ngb_guest_scalar_fallback','ngb_guest_pointer','ngb_poll_due','ngb_guest_high_vector',
    'ngb_vector_read_slow','ngb_vector_write_slow','ngb_ram_span','d3d_hook','d3d_after',
    'ngb_direct_mesh_scope','ngb_direct_try_indexed','ngb_direct_index_reference_done'}:
   targets.add(t);return '\tbl ngb_gate_'+t+'\n'
  return m[0]
 s=re.sub(re.escape(store)+r'\s*(bl|blr)\s+([^\s]+)\n'+re.escape(load),sub,s)
 dst=out/(obj.stem+'.gated.s');dst.write_text(s);sp.run([cc,'-c',dst,'-o',out/(obj.stem+'.o')],check=True)
with cf.ThreadPoolExecutor(3) as ex:list(ex.map(build,old.glob('recomp_*.c.s')))
a=out/'gates.s';a.write_text('.text\n'+''.join(f'.global ngb_gate_{name}\n.type ngb_gate_{name},%function\nngb_gate_{name}:\n'+' stp x29,x30,[sp,-16]!\n mov x29,sp\n'+store+(' blr x16\n' if name=='indirect' else f' bl {name}\n')+load+f' ldp x29,x30,[sp],16\n ret\n.size ngb_gate_{name},.-ngb_gate_{name}\n' for name in sorted(targets|{'indirect'}))+'.section .note.GNU-stack,"",%progbits\n')
sp.run([cc,'-c',a,'-o',out/'gates.o'],check=True);print('shared exit gates',len(targets))
