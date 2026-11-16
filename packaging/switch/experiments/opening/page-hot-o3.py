"""Recompile only sampled hot units using O3, preserving the full-page ABI."""
from pathlib import Path
import os,re,sys
base=Path('build/switch-runtime')
abi=Path('/work/packaging/switch/arm-registers')
next_set='--next' in sys.argv
loop_ira='--loop-ira' in sys.argv
simple_layout='--simple-layout' in sys.argv
compact='--compact-loops' in sys.argv
page_bias='--page-bias' in sys.argv
compact_next='--compact-next' in sys.argv
size_hot='--size-hot' in sys.argv
cold_scalar='--cold-scalar' in sys.argv
block_predicate='--block-predicate' in sys.argv
effective_mask='--effective-mask' in sys.argv
if effective_mask or block_predicate or cold_scalar or size_hot or simple_layout or page_bias or compact_next: compact=True
assert sum([next_set,loop_ira,compact])<=1
d=(base/'core-perf'/('opening-loop-ira' if loop_ira else 'opening-page-next-o3' if next_set else 'opening-page-hot-o3')).resolve();d.mkdir(exist_ok=True)
superblocks='--superblocks' in sys.argv
assert not superblocks or compact
if compact:
    d=d.parent/'opening-compact-loops';d.mkdir(exist_ok=True)
    if superblocks: d=d.parent/'opening-superblocks';d.mkdir(exist_ok=True)
    if effective_mask: d=d.parent/'opening-effective-mask';d.mkdir(exist_ok=True)
    if block_predicate: d=d.parent/'opening-block-predicate';d.mkdir(exist_ok=True)
    if cold_scalar: d=d.parent/'opening-cold-scalar';d.mkdir(exist_ok=True)
    if size_hot: d=d.parent/'opening-size-hot';d.mkdir(exist_ok=True)
    if compact_next: d=d.parent/'opening-compact-next';d.mkdir(exist_ok=True)
    if page_bias: d=d.parent/'opening-page-bias';d.mkdir(exist_ok=True)
    if simple_layout: d=d.parent/'opening-simple-layout';d.mkdir(exist_ok=True)
parent=d.parent/'opening-full-page'
os.environ['NGB_REG_OUT']=str(d)
template=(parent/'template.h').read_text()
def predicate(header):
    if not (block_predicate or effective_mask): return header
    old='if (!(ticket & ngb_poll_mask) || ngb_pending_dpcs)'
    assert header.count(old)==1
    if effective_mask:
        return header.replace(old,'extern unsigned ngb_effective_mask; if (!(ticket & ngb_effective_mask))')
    return header.replace(old,'if (((ticket & ngb_poll_mask) == 0) | (ngb_pending_dpcs != 0))')
template=predicate(template)
decl='uintptr_t ngb_guest_scalar_fallback('
if cold_scalar:
    assert template.count(decl)==1
    template=template.replace(decl,'__attribute__((cold)) '+decl)
s=(abi/'compile.py').read_text().replace("(r/'guest_memory.h').read_text()",repr(template))
s=s.replace('register uint16_t *reg_pages asm("x27");','register uint32_t *reg_ends asm("x27");').replace('#define ngb_fast_page_bytes reg_pages','')
s,n=re.subn(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))',s,flags=re.M);assert n==1
num=r'(?:sub_|d3d_orig_)[0-9A-F]+';s=s.replace(num,'(?:'+num+'|xbe_entry_point)')
names=[f'recomp_{i:04}.c' for i in ((28,1,0,29,15) if next_set or compact_next else (2,10,16,26,39))]
s=s[:s.index("f=o/'entry.S'")].replace('ex.map(build,units)','ex.map(build,'+repr(names)+')')
k=' sp.run(c,cwd=w,check=True)';assert s.count(k)==1
s=s.replace(k," c[-1:-1]=['-O3','-ffp-contract=off','-fno-fast-math','-fno-optimize-sibling-calls']\n"+k)
if compact:
    s=s.replace("'-O3','-ffp-contract=off'","'-O3','-fno-peel-loops','-fno-loop-unroll-and-jam','--param=max-completely-peel-times=0','-ffp-contract=off'")
if '--superblocks' in sys.argv:
    k="'--param=max-completely-peel-times=0'"
    assert s.count(k)==1
    s=s.replace(k,k+",'-fsched2-use-superblocks'")
if size_hot:
    k="'-O3','-fno-peel-loops'"
    assert s.count(k)==1
    s=s.replace(k,"'-Os','-fno-omit-frame-pointer','-fno-peel-loops'")
if page_bias:
    k="'--param=max-completely-peel-times=0'";assert s.count(k)==1
    s=s.replace(k,k+", '--param=builtin-expect-probability=99'")
if simple_layout:
    k="'--param=max-completely-peel-times=0'"
    assert s.count(k)==1
    s=s.replace(k,k+",'-freorder-blocks-algorithm=simple'")
if loop_ira:
    k="'-O3','-ffp-contract=off'"
    assert s.count(k)==1
    s=s.replace(k,"'-O3','-fira-region=all','-fira-loop-pressure','-ffp-contract=off'")
exec(compile(s,'page-o3','exec'),{})
assert (d/'guest_memory.h').read_text()==predicate((parent/'guest_memory.h').read_text()).replace(decl,('__attribute__((cold)) ' if cold_scalar else '')+decl)
exec(compile((abi/'gates.py').read_text(),'page-o3-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
