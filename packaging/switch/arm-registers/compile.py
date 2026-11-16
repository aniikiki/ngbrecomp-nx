from pathlib import Path
import concurrent.futures as cf
import subprocess as sp
import re,os
import shlex
# The regular Switch build supplies both the compiler command and the complete
# public symbol list. Recompile from source every time: stale guest objects
# must never be mixed into an NRO.
w=Path('/work/build/switch-runtime/switch')
r=Path('/work/packaging/switch/runtime')
o=Path(os.environ.get('NGB_REG_OUT',w.parent/'native-regs'))
mode=os.environ.get('NGB_REG_PROFILE','');assert mode in ('','train','use')
o.mkdir(exist_ok=True)
ns=[0,1,2,3,9,10,11,14,16,27,28,29,37,44]
units=[f'recomp_{n:04}.c' for n in ns]
ccs=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines()
symbols=set()
for n in units:
 path=w/'CMakeFiles/ngb_boot_code.dir/work/build/switch-runtime/gen'/n.replace('.c','.o')
 sym=sp.check_output(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-nm','-g','--defined-only',path],text=True)
 for line in sym.splitlines():
  name=line.split()[-1];assert re.fullmatch(r'(?:sub_|d3d_orig_)[0-9A-F]+',name),name;symbols.add(name)
header=o/'regs.h'
header.write_text('#include "switch_guest_regs.h"\n'+''.join(f'#undef g_{a}\nregister unsigned gp_{a} asm("x{i}");\n#define g_{a} gp_{a}\n' for i,a in enumerate(['eax','ecx','edx','esp','ebx','esi','edi'],19)))
# The assembly bridges address the first seven 32-bit fields directly.
with header.open('a') as h:
 for i,name in enumerate(('eax','ecx','edx','esp','ebx','esi','edi')):
  h.write(f'_Static_assert(__builtin_offsetof(RecompRegs,r_{name})=={4*i},"register file layout");\n')
store='\tstp w19, w20, [x28]\n\tstp w21, w22, [x28, 8]\n\tstp w23, w24, [x28, 16]\n\tstr w25, [x28, 24]\n'
load=store.replace('stp','ldp').replace('str','ldr')
mem=(r/'guest_memory.h').read_text()
needle='extern unsigned char *ngb_fast_ram;'
assert mem.count(needle)==1
mem=mem.replace(needle,needle+'\nregister unsigned char *reg_ram asm("x26");\nregister uint16_t *reg_pages asm("x27");\n#define ngb_fast_ram reg_ram\n#define ngb_fast_page_bytes reg_pages\n')
(o/'guest_memory.h').write_text(mem)
pure=set('memcpy memmove memset memcmp sin cos tan sqrt sqrtf atan2 log fmod exp2 __aarch64_read_tp recomp_lookup recomp_lookup_manual recomp_lookup_kernel'.split())
def build(n):
 c=next(shlex.split(x) for x in ccs if x.endswith('/'+n));c[c.index('-o')+1]=str(o/(n+'.native.s'));c[c.index('-MF')+1]=str(o/(n+'.d'));c[c.index('-c')]='-S';c[1:1]=['-I'+str(o),'-include',str(header)];c.insert(-1,'-g0');c.insert(-1,'-ffixed-x28');c.insert(-1,'-fno-ipa-ra');c.insert(-1,'-fno-optimize-sibling-calls')
 if mode:
  c.insert(-1,'-fprofile-dir='+str(o/'profiles'))
  flags=['-fprofile-arcs','-fprofile-info-section=ngb_training','-fprofile-update=single'] if mode=='train' else ['-fprofile-use','-fno-profile-values','-fprofile-partial-training','-Werror=missing-profile','-Werror=coverage-mismatch','-fno-reorder-blocks-and-partition','-fno-ipa-cp-clone']
  c[-1:-1]=flags
 sp.run(c,cwd=w,check=True)
 asm=(o/(n+'.native.s')).read_text();(o/(n+'.native.s')).unlink();defs=set(re.findall(r'^\s*\.global\s+(\w+)',asm,re.M))&symbols
 # Only branch and label references, never addresses placed in tables, use the fast ABI.
 lines=[]
 for ln in asm.splitlines(True):
  mt=re.match(r'^\s*(bl|blr)\s+([^\s]+)',ln)
  if mt:
   op,t=mt.groups();local=t.removesuffix('.localalias')
   if t in symbols:ln=ln.replace(t,'ngb_reg_'+t,1)
   elif local in defs or t.startswith('.L') or t in pure or t in ('XMM_MEM','XMM_STORE'):pass
   else:ln=store+ln+load
  elif any(token in ln for token in ('.global','.type','.size','.set')) or ln.rstrip().endswith(':'):
   ln=re.sub(r'(?<![\w.])((?:sub_|d3d_orig_)[0-9A-F]+)\b(?!\.)',lambda m:'ngb_reg_'+m[1] if m[1] in defs else m[1],ln)
  lines.append(ln)
 out=''.join(lines)
 raw=out.splitlines(True)
 where={ln.strip()[:-1]:i for i,ln in enumerate(raw) if ln.startswith('.L') and ln.strip().endswith(':')}
 for i,ln in enumerate(raw):
  m=re.fullmatch(r'\s*(tbz|tbnz)\s+([^,]+),\s*([^,]+),\s*(\.L\w+)\s*',ln)
  if m and abs(where[m[4]]-i)>5900:
   inv='tbz' if m[1]=='tbnz' else 'tbnz'
   raw[i]=f'\t{inv} {m[2]}, {m[3]}, .+8\n\tb {m[4]}\n'
 out=''.join(raw)
 # Internal helpers are compiled with register globals, including out-of-line
 # functions selected by GCC. Their external slow paths already synchronize.
 (o/(n+'.s')).write_text(out)

with cf.ThreadPoolExecutor(3) as ex:list(ex.map(build,units))
f=o/'entry.S'
f.write_text('.text\n'+''.join(f'.section .text.{n},"ax",%progbits\n.p2align 2\n.global {n}\n.type {n},%function\n{n}:\n'+
 ' stp x29,x30,[sp,-96]!\n mov x29,sp\n stp x19,x20,[sp,16]\n stp x21,x22,[sp,32]\n stp x23,x24,[sp,48]\n stp x25,x26,[sp,64]\n stp x27,x28,[sp,80]\n adrp x26,ngb_fast_ram\n ldr x26,[x26,:lo12:ngb_fast_ram]\n adrp x27,ngb_fast_page_bytes\n add x27,x27,:lo12:ngb_fast_page_bytes\n adrp x28,g_regs\n add x28,x28,:lo12:g_regs\n'+load+f' bl ngb_reg_{n}\n'+store+
 ' ldp x19,x20,[sp,16]\n ldp x21,x22,[sp,32]\n ldp x23,x24,[sp,48]\n ldp x25,x26,[sp,64]\n ldp x27,x28,[sp,80]\n ldp x29,x30,[sp],96\n ret\n'+f'.size {n},.-{n}\n' for n in sorted(symbols))+'.section .note.GNU-stack,"",%progbits\n')
sp.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc','-c',f,'-o',o/'entry.o'],check=True)
print('entry wrappers',len(symbols))
