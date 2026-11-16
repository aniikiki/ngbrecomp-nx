"""Fold only a null command list at the three known model submission sites.
The ordinary stack and non-service ticket are checked *before* changing state."""
import os,re
from pathlib import Path
root=Path('build/switch-runtime')
helper=r'''
extern uint64_t ngb_reg_entries;
extern unsigned ngb_reg_current_va,ngb_reg_recent[32];
static inline __attribute__((always_inline)) int empty_material(unsigned ret) {
 if(eax)return 0;
 unsigned lo=esp-8;
 if((lo&3u) || (lo&4095u)+8u>ngb_fast_page_bytes[lo>>12])return 0;
 uint64_t next=ngb_guest_polls+1;
 if(!(next&ngb_poll_mask)||ngb_pending_dpcs||ngb_reg_entries<48)return 0;
 volatile unsigned *q=(volatile unsigned *)(ngb_fast_ram+(lo&0x7fffffffu));
 q[1]=ret;
 ngb_reg_current_va=0x30c240;
 ngb_reg_recent[ngb_reg_entries++&31]=0x30c240;
 ngb_guest_polls=next;
 q[0]=esi;
 esi=q[0];
 return 1;
}
'''
def transform(s):
    pat=r'PUSH32\(esp, (0x[0-9A-F]+u)\); RECOMP_ABI_CALL\(0x0030C240u, sub_0030C240\);'
    s,n=re.subn(pat,lambda m:'if(!empty_material('+m[1]+')) { '+m[0]+' }',s)
    assert n==3
    return s.replace('#include "recomp_funcs.h"','#include "recomp_funcs.h"\n'+helper)
if __name__=='__main__':
    abi=Path('/work/packaging/switch/arm-registers')
    d=(root/'core-perf/opening-empty-material').resolve();d.mkdir(exist_ok=True)
    n='recomp_0028.c';(d/n).write_text(transform((root/'gen'/n).read_text()))
    os.environ['NGB_REG_OUT']=str(d)
    s=(abi/'compile.py').read_text()
    s=re.sub(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))',s,flags=re.M)
    num=r'(?:sub_|d3d_orig_)[0-9A-F]+'
    s=s.replace(num,'(?:'+num+'|xbe_entry_point)')
    s=s[:s.index("f=o/'entry.S'")].replace('ex.map(build,units)',"ex.map(build,['recomp_0028.c'])")
    s=s.replace(' sp.run(c,cwd=w,check=True)'," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\n sp.run(c,cwd=w,check=True)")
    exec(compile(s,'empty-material','exec'),{})
    exec(compile((abi/'gates.py').read_text(),'material-gates','exec'),{})
    for f in [*d.glob('recomp_*.s'),d/n]:f.unlink()
