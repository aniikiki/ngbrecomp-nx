"""Preserve scope across Switch guest worker/fiber switches during Linux CPU sampling."""
def install(p,r,probe):
 w=(r/'workers.inc').read_text()
 for typ in ('worker','fiber'):
  k='static struct '+typ+' {';assert w.count(k)==1
  w=w.replace(k,k+'\n sig_atomic_t xdk_depth;')
 for dest in ('dest','next'):
  k=f'ngb_ctx_switch(&old->sp, {dest}->sp);';assert w.count(k)==1
  w=w.replace(k,f'old->xdk_depth=pc_xdepth;pc_xdepth={dest}->xdk_depth;'+k)
 (p.out/'pc-scope-workers.inc').write_text(w)
 f=p.out/'origin-runtime.inc';s=f.read_text();k='#include "workers.inc"';assert s.count(k)==1;f.write_text(s.replace(k,'#include "pc-scope-workers.inc"'))
 k='static volatile sig_atomic_t pc_used';probe=probe.replace(k,'static volatile sig_atomic_t pc_xdepth;\nvoid pc_d3d_enter(void){pc_xdepth++;}\nvoid pc_d3d_leave(void){if(pc_xdepth<=0)abort();pc_xdepth--;}\n'+k)
 probe=probe.replace('unsigned frame;}','unsigned frame,scope;}').replace('pc_rows[pc_used].pc=', 'pc_rows[pc_used].scope=pc_xdepth;pc_rows[pc_used].pc=',1)
 k=' for(int j=0;j<pc_used;j++)fprintf(stderr,"[FRAME_PC]';assert probe.count(k)==1
 return probe.replace(k,' for(int j=0;j<pc_used;j++)fprintf(stderr,"[D3D_SCOPE_PC] %u %u %lx\\n",pc_rows[j].frame,pc_rows[j].scope,(unsigned long)pc_rows[j].pc);\n'+k)
