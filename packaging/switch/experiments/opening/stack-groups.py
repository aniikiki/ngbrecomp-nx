"""Coalesce adjacent guest push/pop/constant-offset ESP loads in sampled functions."""
from pathlib import Path
import re,sys,subprocess as sp,shlex,tempfile,runpy
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parents[1]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
d=p.out; abi=RUNTIME.parent/'arm-registers'
api=runpy.run_path(str(RUNTIME.parent/'analyze-profile.py'))
rel=BASE/'history/0.51.0-rc1';sym=api['load_symbols'](rel/'symbols.gz')
rows=api['parse_windows']((BASE/json.loads((rel/'deployment.json').read_text())['hardware_log']).read_text().splitlines())[1,120]['profiles']['guest'][1]
wanted={sym(pc).split('.localalias')[0].removeprefix('ngb_reg_') for row in rows if 1<=row[0]<=120 for pc in row[-1]}
private=set(re.findall(r'^\.global (\w+)',(REGS/'entry.S').read_text(),re.M))
ccs=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=BASE/'switch',text=True).splitlines()
reg=r'(?:eax|ecx|edx|ebx|esi|edi|ebp)'
op=re.compile(r'    (?:(PUSH|POP)32\(esp, ('+reg+r'|0x[0-9A-Fa-f]+u?|\d+)\)|('+reg+r') = MEM32\(esp(?: ([+-]) (0x[\da-fA-F]+|\d+))?\));\n')
def grouped(body):
 global sites
 def sub(m):
  global sites
  seq=list(op.finditer(m[0]));assert ''.join(x[0] for x in seq)==m[0]
  delta=0;steps=[]
  for x in seq:
   if x[1]=='PUSH':delta-=4
   pos=delta+(int(x[5],0)*(-1 if x[4]=='-' else 1) if x[5] else 0)
   steps.append((pos,x))
   if x[1]=='POP':delta+=4
  lo=min(v for v,x in steps);hi=max(v for v,x in steps)+4
  if hi-lo>256 or any(v%4 for v,x in steps):return m[0]
  sites+=1
  fast=[];ref=[]
  for v,x in steps:
   dest=f'q[{(v-lo)//4}]'
   fast.append(dest+'='+x[2]+';' if x[1]=='PUSH' else (x[2] or x[3])+'='+dest+';')
   ref.append(f'if((uintptr_t)&{dest}!=ngb_guest_scalar(esp+({v}),4))__builtin_trap();')
  # Do not alter SP until all accesses complete: no RHS refers to ESP, all
  # destinations are ordinary registers/guest RAM and no calls can intervene.
  return ('    {uint32_t a=esp+('+str(lo)+');unsigned off=a&4095; if(!(a&3) && off+'+str(hi-lo)+'<=ngb_fast_page_bytes[a>>12]){volatile uint32_t *q=(volatile uint32_t*)(ngb_fast_ram+(a&0x7fffffffu));\n#ifdef STACK_AUDIT\n++group_hits;group_ops+='+str(len(seq))+';'+''.join(ref)+'\n#endif\n'+''.join(fast)+f'esp+=({delta});'+'}else{\n#ifdef STACK_AUDIT\n++group_fallback;\n#endif\n'+m[0]+'}}\n')
 return re.sub('(?:'+op.pattern+'){2,}',sub,body)
if '--check' in sys.argv:
 # Execute every distinct generated input sequence on synthetic stacks with
 # independent RAM snapshots. After each run compare the entire RAM, all guest
 # registers and the ordered slow-access log, including partial/protected pages.
 sites=0;blocks=set()
 for f in REGS.glob('*.gated.s'):
  source=(BASE/'gen'/f.name.split('.gated')[0]).read_text()
  for m in re.finditer(r'^void ((?:sub_|d3d_orig_)\w+)\(void\)\n\{.*?^\}',source,re.M|re.S):
   if m[1] in wanted & private:
    blocks.update(x[0] for x in re.finditer('(?:'+op.pattern+'){2,}',m[0]))
 blocks=sorted(b for b in blocks if grouped(b)!=b)
 with tempfile.TemporaryDirectory(dir=d) as tmp:
  tmp=Path(tmp);src=tmp/'check.c';exe=tmp/'check'
  code=here.joinpath('stack-groups-check.inc').read_text()
  for ref in (True,False):
   code+='\nstatic void '+('reference' if ref else 'candidate')+'(unsigned i){switch(i){\n'
   for i,b in enumerate(blocks):code+=f'case {i}: {{'+(b if ref else grouped(b))+'}break;\n'
   code+='default: abort();}}\n'
  src.write_text(code+f'\nint main(void){{return check({len(blocks)});}}\n')
  sp.run(['cc','-O1','-fno-strict-aliasing',src,'-o',exe],check=True);sp.run([exe],check=True)
 sys.exit()
if '--link' in sys.argv:
 for o in sorted(d.glob('group-*.o')):
  if o.name.startswith('group-orig-'):
   n=o.name[len('group-orig-'):];p.link[p.link.index(str(REGS/n))]=str(o)
  elif not o.name.startswith('group-ctrl-') or '--matched' in sys.argv:p.link.insert(1,str(o))
 p.driver(r'''
unsigned span_arm,span_control; unsigned long long group_hits,group_ops,group_fallback;
void span_frame(unsigned f,unsigned draws){
 static unsigned prev;static uint64_t last;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,span_arm,(unsigned long long)(now-last),draws-prev);
 if(f==120)fprintf(stderr,"[STACK_GROUPS] %llu %llu %llu\n",group_hits,group_ops,group_fallback);
 span_arm=f<120 && (getenv("NGB_OPEN_CHECK")||((((f/2+12345)*2654435761u>>31)^(f&1))^(getenv("NGB_OPEN_REVERSE")!=NULL)));
 span_control=f>=120?0:1+!span_arm; last=now;prev=draws;
}
''')
 s=(RUNTIME/'scene/bridge.c').read_text()
 for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
  assert s.count(k)==1;s=s.replace(k,k+f' extern void span_frame(unsigned,unsigned);span_frame({arg},draws);')
 p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish();sys.exit()
cc='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc'
pure=set('memcpy memmove memset memcmp sin cos tan sqrt sqrtf atan2 log fmod exp2 __aarch64_read_tp recomp_lookup recomp_lookup_manual recomp_lookup_kernel'.split())
gates=set(re.findall(r'^\.global (ngb_gate_\w+)',(REGS/'gates.s').read_text(),re.M))
save='stp w19,w20,[x28]\nstp w21,w22,[x28,#8]\nstp w23,w24,[x28,#16]\nstr w25,[x28,#24]\n'
sites=nf=0
with tempfile.TemporaryDirectory(dir=d) as tmp:
 tmp=Path(tmp)
 for f in sorted(REGS.glob('*.gated.s')):
  name=f.name.split('.gated')[0];source=(BASE/'gen'/name).read_text();ls=[];names=[]
  for m in re.finditer(r'^void ((?:sub_|d3d_orig_)\w+)\(void\)\n\{.*?^\}',source,re.M|re.S):
   n=m[1]
   if n not in wanted or n not in private:continue
   b=grouped(m[0]); 
   if b!=m[0]:ls.append((m[0] if '--control' in sys.argv else b).replace('void '+n+'(', 'void group_'+n+'(',1));names.append(n)
  if not ls:continue
  nf+=len(ls)
  src=tmp/name;src.write_text(source.split('/**\n * sub_',1)[0].split('/**\n * d3d_orig_',1)[0]+'\nextern unsigned long long group_hits,group_ops,group_fallback;\n'+'\n'.join(ls))
  c=next(shlex.split(x) for x in ccs if x.endswith('/'+name));c[c.index('-o')+1]=str(tmp/'alt.s');c[c.index('-MF')+1]=str(tmp/'deps');c[c.index('-c')]='-S';c[1:1]=['-I'+str(REGS),'-include',str(REGS/'regs.h')];c[-1:]=['-g0','-ffixed-x28','-fno-ipa-ra','-fno-optimize-sibling-calls',*(['-DSTACK_AUDIT'] if '--audit' in sys.argv else []),str(src)]
  sp.run(c,cwd=BASE/'switch',check=True)
  asm=(tmp/'alt.s').read_text();local=set(re.findall(r'^\s*\.type\s+([\w.]+), %function',asm,re.M))
  def bridge(m):
   op,t=m.groups()
   if op=='blr':return ' mov x16,'+t+'\n bl ngb_gate_indirect'
   if t in private:return ' bl ngb_reg_'+t
   if t=='ngb_checkpoint':return ' bl ngb_reg_checkpoint'
   if t.startswith('.L') or t in local or t in pure:return m[0]
   if 'ngb_gate_'+t in gates:return ' bl ngb_gate_'+t
   return save+m[0]+'\n'+save.replace('stp','ldp').replace('str','ldr')
  asm=re.sub(r'(?m)^\s*(bl|blr)\s+([^\s]+)$',bridge,asm);(tmp/'alt.s').write_text(asm)
  if '--control' in sys.argv:
   # Compile the unchanged bodies under the same flags and symbol boundaries.
   ctrl=re.sub(r'\bgroup_((?:sub_|d3d_orig_)\w+)',r'ctrl_\1',asm)
   a=tmp/'unit.s';a.write_text(ctrl);sp.run([cc,'-c',a,'-o',d/('group-ctrl-'+name+'.o')],check=True)
  for label,body in ([('orig',f.read_text())] if '--control' in sys.argv else [('alt',asm),('orig',f.read_text())]):
   if label=='orig':
    for n in names:
     k='ngb_reg_'+n+':\n';assert body.count(k)==1
     stub=(' adrp x16,span_control\n ldr w16,[x16,:lo12:span_control]\n cbz w16,1f\n tbz w16,#0,2f\n b group_'+n+'\n2: b ctrl_'+n+'\n1:\n' if '--control' in sys.argv else ' adrp x16,span_arm\n ldr w16,[x16,:lo12:span_arm]\n cbz w16,1f\n b group_'+n+'\n1:\n')
     body=body.replace(k,k+stub)
   a=tmp/'unit.s';a.write_text(body);sp.run([cc,'-c',a,'-o',d/('group-'+label+'-'+name+'.o')],check=True)
 print('sampled functions',nf,'groups',sites,flush=True)
