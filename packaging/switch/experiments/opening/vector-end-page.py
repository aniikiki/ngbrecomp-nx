"""Reuse the private ABI's existing exclusive scalar bound for complete 16-byte reads/writes."""
from pathlib import Path
import runpy
p=Path(__file__).parent;b=Path('build/switch-runtime')
units=[2,10,16,28,29]
def transform(s,u):
 d=b/'core-perf/opening-vector-end-page'
 h=(b/'gen/recomp_types.h').read_text()
 a=h.index('RecompXmm XMM_MEM(uint32_t addr)');z=h.index('/* movlps',a)
 old='(addr & 4095u) + 16u <= ngb_fast_page_bytes[addr >> 12]'
 assert h[a:z].count(old)==2
 (d/'recomp_types.h').write_text(h[:a]+h[a:z].replace(old,'(uint64_t)addr + 12u < reg_ends[addr >> 12]')+h[z:])
 (d/'recomp_funcs.h').write_bytes((b/'gen/recomp_funcs.h').read_bytes());return s
if __name__=='__main__':
 count=0
 for page in (0,7,8,0xfff,0x1000,0x1180,0x80000,0x87fff,0xfffff):
  for mapped in (True,False):
   limit=((page<<12)+4093) if mapped else 0
   for off in range(4096):
    assert (off+16 <= (4096 if mapped else 0))==(((page<<12)+off+12)<limit)
    count+=1
 print('checked aligned and unaligned vector range decisions:',count,flush=True)
 runpy.run_path(str(p/'model-copy.py'))['build']('vector-end-page',[(True,[2,10,16]),(False,[28,29])],transform)
