"""Build 0.52 diagnostic NRO without touching the baseline. Reuse its exact objects and RomFS."""
from pathlib import Path
import subprocess as sp, shlex,tempfile,re,hashlib,struct
here=Path(__file__).resolve().parent
w=Path('/work/build/switch-runtime');b=w/'switch';regs=w/'native-regs';r=Path('/work/packaging/switch/runtime')
out=w/'history/0.52.1-diag';out.mkdir(exist_ok=True)
sdk=Path('/opt/devkitpro');gcc=sdk/'devkitA64/bin/aarch64-none-elf-gcc'
commands=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=b,text=True).splitlines()
link=shlex.split(commands[-1].split('&&')[1]);extra=[]
def one(s,a,z):
 assert s.count(a)==1,a
 return s.replace(a,z)
def comp(name,s,flags=[]):
 c=next(shlex.split(l) for l in commands if l.endswith('/'+name))
 f=d/name.split('/')[-1];f.write_text(s);o=str(f)+'.o';old=c[c.index('-o')+1]
 c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[1:1]=['-I'+str(Path(c[-1]).parent),*flags];c[-1]=str(f);sp.run(c,cwd=b,check=True)
 if old in link:link[link.index(old)]=o
 else:extra.append(o)
def around(s,signature,key):
 k=s.index(signature+'\n{');a=s.index('{',k)+1
 return s[:a]+f'\n unsigned rb_saved __attribute__((cleanup(rb_restore)))=ngb_rb_set({key});\n'+s[a:]
decl='extern unsigned ngb_rb_set(unsigned);\nstatic inline void rb_restore(unsigned *s){ngb_rb_set(*s);}\n'
tags=['000320E0','001CB9A0','001CA790','001CC300','001CBA70','001CC5A0','001CBD00','00020040','0001FB60','001CB3B0','001CB510','001CB550','001CB260']
with tempfile.TemporaryDirectory(dir=out) as temp:
 d=Path(temp)
 s=(r/'direct/hooks.c').read_text()
 s=one(s,'static void charge_scope(void)',(here/'remainder-clock.inc').read_text()+'\nstatic void charge_scope(void)')
 s=one(s,'    uint64_t delta = now - index_time.edge;', '    rb_tick(now);\n    uint64_t delta = now - index_time.edge;')
 s=one(s,'    measured_frames += ngb_direct_detail_frame;', '    rb_finish(completed);\n    measured_frames += ngb_direct_detail_frame;')
 s=one(s,'    if (ngb_direct_detail_frame) index_time.edge = ngb_elapsed_ns();','    if (ngb_direct_detail_frame) index_time.edge = ngb_elapsed_ns();\n    rb_active=completed<120 && ngb_direct_detail_frame;rb_edge=index_time.edge;')
 s=one(s,'    ngb_direct_detail_frame = 1;\n    index_time.edge = ngb_elapsed_ns();','    ngb_direct_detail_frame = 1;\n    index_time.edge = ngb_elapsed_ns();rb_start();')
 s=one(s,'    ngb_direct_detail_frame = 0;', '    ngb_direct_detail_frame = 0;rb_active=0;')
 comp('direct/hooks.c',s)
 s=(r/'workers.inc').read_text()
 for word in ['worker','fiber']:s=one(s,'static struct '+word+' {','static struct '+word+' {\n unsigned rb_saved;')
 for name in ['dest','next']:
  k=f'ngb_ctx_switch(&old->sp, {name}->sp);';s=one(s,k,'old->rb_saved=ngb_rb_set('+name+'->rb_saved);\n    '+k)
 (d/'workers.inc').write_text(s)
 s=decl+(r/'runtime.c').read_text()
 for signature,key in [('void ngb_poll_due(uint64_t ticket)','0xff000001'),('static void poll_callbacks(void)','0xff000002')]:s=around(s,signature,key)
 s=s.replace('0.51.0-rc1;', '0.52.1-diag;');comp('runtime.c',s,['-DNGB_REGISTER_PACKAGE','-DNGB_RIGID_CLIP'])
 s=decl+(r/'nv2a_boot.c').read_text();s=around(s,'static void execute_dma(uint32_t put)','0xff000003');comp('nv2a_boot.c',s)
 comp('main.c',(r/'main.c').read_text().replace('0.51.0-rc1','0.52.1-diag'),['-DNGB_REGISTER_PACKAGE','-DNGB_RIGID_CLIP'])
 seen=set()
 for obj in sorted(regs.glob('recomp_*.c.o')):
  s=obj.with_suffix('.gated.s').read_text();orig=s
  for tag in tags:
   k='ngb_reg_sub_'+tag+':\n'
   if k not in s:continue
   seen.add(tag);s=one(s,k,k+f''' stp x29,x30,[sp,#-32]!
 mov x29,sp
 mov w0,#{int(tag,16)&65535}
 movk w0,#{int(tag,16)>>16},lsl #16
 bl ngb_rb_set
 str w0,[sp,#16]
 bl .Lrb{tag}
 ldr w0,[sp,#16]
 bl ngb_rb_set
 ldp x29,x30,[sp],#32
 ret
.Lrb{tag}:
''')
  if 'ngb_reg_sub_0030C8B0:\n' in s:
   a=s.index('ngb_reg_sub_0030C8B0:\n');z=s.index('\t.size\tngb_reg_sub_0030C8B0',a);part=s[a:z]
   # Save callback VA in the unused 4-byte local at native SP+16. Scope
   # only the indirect call; never label the subsequent scheduler as its task.
   part=one(part,'\tadrp\tx3, :got:g_icall_trace',' str w2,[sp,#16]\n\tadrp\tx3, :got:g_icall_trace')
   k='mov x16,x0\n\tbl ngb_gate_indirect';part=one(part,k,''' mov x16,x0
 ldr w0,[sp,#16]
 stp x16,x30,[sp,#-16]!
 bl ngb_rb_set
 ldp x16,x30,[sp],#16
 str w0,[sp,#16]
 bl ngb_gate_indirect
 ldr w0,[sp,#16]
 bl ngb_rb_set''')
   s=s[:a]+part+s[z:];seen.add('dispatch')
  o=obj
  if s!=orig:
   a=d/'rb.s';a.write_text(s);o=d/obj.name;sp.run([gcc,'-c',a,'-o',o],check=True)
  ix=next(i for i,x in enumerate(link) if x.endswith('/'+obj.name.replace('.c.o','.o')));link[ix]=str(o)
 assert seen==set(tags)|{'dispatch'},seen
 link[1:1]=[*extra,*map(str,[regs/'backend-clip.o',regs/'entry.o',regs/'gates.o',regs/'checkpoint.o'])]
 elf=d/'diag.elf';link[link.index('-o')+1]=str(elf);sp.run(link,cwd=b,check=True)
 import gzip
 names=sp.check_output([sdk/'devkitA64/bin/aarch64-none-elf-nm','-n','-S',elf])
 (out/'symbols.gz').write_bytes(gzip.compress(names,mtime=0))
 nacp=d/'diag.nacp';nro=out/'ngb-startup.nro';sp.run([sdk/'tools/bin/nacptool','--create','NGB Startup','NGB port development','0.52.1-diag',nacp],check=True)
 sp.run([sdk/'tools/bin/elf2nro',elf,nro,'--nacp='+str(nacp),'--icon='+str(sdk/'libnx/default_icon.jpg'),'--romfsdir='+str(w/'romfs')],check=True)
 def asset(path,slot):
  with path.open('rb') as f:
   f.seek(0x18);base=int.from_bytes(f.read(4),'little');f.seek(base);assert f.read(4)==b'ASET'
   f.seek(base+8+16*slot);off,size=struct.unpack('<QQ',f.read(16));f.seek(base+off);return hashlib.sha256(f.read(size)).digest()
 assert asset(nro,1)==hashlib.sha256(nacp.read_bytes()).digest() and asset(nro,2)==asset(w/'history/0.51.0-rc1/ngb-startup.nro',2)
 print('verified',nro,nro.stat().st_size,flush=True)
