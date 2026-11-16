"""Guard individual linked private call sites, leaving symbol lookup and the public ABI unchanged."""
from pathlib import Path
import bisect,struct,subprocess as sp,mmap
def syms(lines):
 out={}
 for l in lines.splitlines():
  v=l.split()
  if len(v)==4 and v[2] in 'tTwW':out[v[3]]=tuple(int(i,16) for i in v[:2])
 return out
def guard(stub,*targets):
 assert 1<=len(targets)<=4
 asm=f'.p2align 2\n.global {stub}\n.type {stub},%function\n{stub}:\n'
 for target in targets:
  asm+=f' adrp x17,{target}\n add x17,x17,:lo12:{target}\n cmp x16,x17\n b.ne 1f\n b ngb_reg_{target}\n1:\n'
 return asm+f' b ngb_gate_indirect\n.size {stub},.-{stub}\n'
def install(p):
 import runpy
 r=runpy.run_path(str(Path(__file__).with_name('gate-pairs-report.py')))
 asm='.text\n';sites=[]
 for pc,c in sorted(r['rows'][30].items()):
  keys=r['keys'];a=keys[bisect.bisect_right(keys,pc)-1];n,fn=r['starts'][a]
  targets=[next(iter(r['names'][t]&r['wrappers'])) for t,count in c.most_common(4) if count>=30 and count>=.05*sum(c.values()) and len(r['names'].get(t,set())&r['wrappers'])==1]
  if not targets:continue
  if not fn.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):continue
  assert pc<a+n
  stub=f'opening_gate_site_{len(sites)}'
  # No change to argument registers or the link register on the miss path.
  asm+=guard(stub,*targets)
  sites.append((fn,pc-a,n,stub))
 assert sites
 asm+='.section .note.GNU-stack,"",%progbits\n'
 f=p.out/'gate-sites.s';f.write_text(asm);o=f.with_suffix('.o');sp.run(['cc','-c',f,'-o',o],check=True)
 p.link[1:1]=[str(o),'-Wl,-u,opening_gate_site_0'];return sites
def patch(f,sites):
 sy=syms(sp.check_output(['nm','-nS','--defined-only',f],text=True))
 with f.open('r+b') as h,mmap.mmap(h.fileno(),0) as buf:
  u=lambda fmt,o:struct.unpack_from('<'+fmt,buf,o)
  ph=[u('IIQQQQQQ',u('Q',32)[0]+i*u('H',54)[0]) for i in range(u('H',56)[0])]
  writes=[]
  for fn,off,size,stub in sites:
   a,n=sy[fn];assert n==size and off<n
   pc=a+off;seg,=[v for v in ph if v[0]==1 and v[1]&1 and v[3]<=pc<v[3]+v[5]]
   fileoff=pc-seg[3]+seg[2]
   def bl(dst):
    rel=dst-pc;assert rel%4==0 and -(1<<27)<=rel<(1<<27)
    return 0x94000000|((rel//4)&0x3ffffff)
   assert u('I',fileoff)[0]==bl(sy['ngb_gate_indirect'][0]),fn
   writes.append((fileoff,bl(sy[stub][0])))
  assert len(writes)==len(set(x for x,_ in writes))
  for off,w in writes:struct.pack_into('<I',buf,off,w)
 print('verified guarded indirect call sites',len(writes),flush=True)
