"""Specialize only observed no-op hooks or an already taken state write.
The slow ABI remains authoritative during initialization and after shutdown."""
import re,runpy,subprocess
from pathlib import Path
def install(p,regs,audit):
 root=Path('/work')
 orig=(root/'src/d3d/hle.cpp').read_text()
 hook=(root/'packaging/switch/runtime/direct/hooks.c').read_text()
 wrap=(root/'src/d3d/d3d_hooks.c').read_text()
 funcs=(root/'src/d3d/d3d_funcs.h').read_text()
 ids={k:int(i) for k,i in re.findall(r'(D3DF_\w+) = (\d+)',funcs)}
 tracked=set(re.findall(r'case (D3DF_\w+)',hook.split('static int material_call(int fn)')[1].split('default:')[0]))
 tracked.update(('D3DF_D3DDevice_DrawIndexedVertices','D3DF_Direct3D_CreateDevice','D3DF_D3DDevice_Swap'))
 after=set(re.findall(r'case (D3DF_\w+)',orig.split('void After(int fn, Call c)')[1].split('default:')[0]))
 exclude=tracked|after
 pre='extern "C" { unsigned char op_idle[D3DF_COUNT]; uint32_t *op_simple; }\n'
 orig=orig.replace('gpu::State g_state;',pre+'gpu::State g_state;')
 k='    bool took = Before(fn, Call{regs});'
 assert orig.count(k)==1
 orig=orig.replace(k,k+'''
    if (g_started && g_backend && !g_mirror && unsigned(fn)<D3DF_COUNT) {
        if(!op_idle[fn] && !g_take[fn] && g_before_idle[fn].load(std::memory_order_relaxed)) op_idle[fn]=1;
        if(!op_simple && g_take[D3DF_D3DDevice_SetRenderState_Simple]) op_simple=g_state.simple.data();
    }''')
 k='    captured_index_stack = 0;\n    compact_indices'
 assert orig.count(k)==1;orig=orig.replace(k,'    op_simple=nullptr; std::memset(op_idle,0,sizeof(op_idle));\n'+k)
 p.add('hle.cpp',orig)
 f=p.out/'hle-leaf.S';o=f.with_suffix('.o')
 runpy.run_path(str(Path(__file__).with_name('d3d-private.py')))['generate'](root,regs,f)
 gates=f.read_text();n=0
 for va,fn in re.findall(r'void sub_([0-9A-F]+)\(void\)\s*/\* \w+ \*/\s*\{\s*if \(!d3d_hook\((D3DF_\w+)\)\) \{\s*d3d_orig_\1\(\);\s*d3d_after\(\2\);\s*\}\s*\}',wrap):
  key=f'ngb_gate_sub_{va}:\n'
  if fn in exclude or key not in gates or f' bl ngb_reg_d3d_orig_{va}\n' not in gates.split(key)[1].split(' ret\n',1)[0]:continue
  # Never bypass a hook until g_backend exists and the public Before actually
  # hit its default arm. No other hook side effects in the Switch direct driver.
  code=f' adrp x9,op_idle\n add x9,x9,:lo12:op_idle\n ldrb w9,[x9,#{ids[fn]}]\n cbz w9,8f\n b ngb_reg_d3d_orig_{va}\n8:\n'
  if fn=='D3DF_D3DDevice_SetRenderState_Simple':
   code=' adrp x9,op_simple\n ldr x9,[x9,:lo12:op_simple]\n cbz x9,8f\n and w10,w20,#0x1ffc\n str w21,[x9,w10,uxtw]\n mov w19,wzr\n add w22,w22,#4\n ret\n8:\n'
  gates=gates.replace(key,key+code);n+=1
 assert n>30
 f.write_text(gates);subprocess.run(['cc','-c',f,'-o',o],check=True)
 p.link[p.link.index(str(regs/'gates.o'))]=str(o)
