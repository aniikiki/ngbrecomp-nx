"""Classify only the interrupted PC, never a caller or every instruction near a check."""
import collections,gzip,hashlib,json,re,runpy,subprocess,sys
from pathlib import Path
here=Path(__file__).resolve().parent
api=runpy.run_path(str(here.parents[1]/'analyze-profile.py'))
base=Path('build/switch-runtime'); release=base/'history/0.51.0-rc1'
elf=base/'native-regs/ngb-startup.elf'; nro=release/'ngb-startup.nro'
dep=json.loads((release/'deployment.json').read_text())
with nro.open('rb') as f:
    hdr=f.read(128); f.seek(0)
    h=hashlib.sha256()
    for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
assert h.hexdigest()==dep['sha256']
b='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-'
def run(*a):return subprocess.check_output(a,text=True)
bid=re.search(r'Build ID: (\w+)',run(b+'readelf','-n',elf))[1]
assert bytes.fromhex(bid)==hdr[64:84]
sym=api['load_symbols'](release/'symbols.gz')
rows=api['parse_windows']((base/dep['hardware_log']).read_text().splitlines())[1,120]['profiles']['guest'][1]
pcs0=[r[-1][0] for r in rows if 1<=r[0]<=120]
lines=run(b+'addr2line','-e',elf,*map(hex,pcs0)).splitlines()
assert len(lines)==len(pcs0)
source=dict(zip(pcs0,lines))
counts=collections.Counter();tasks=collections.Counter(); detail=[]
with nro.open('rb') as f:
 for frame,worker,_,_,_,pcs in rows:
    if not 1<=frame<=120:continue
    pc=pcs[0]; name=sym(pc); f.seek(pc)
    word=f.read(4)[::-1].hex()
    raw=run(b+'objdump','-d','--start-address='+hex(pc),'--stop-address='+hex(pc+8),elf)
    m=re.search(r'^\s*[0-9a-f]+:\s+([0-9a-f]{8})\s+(.+)$',raw,re.M)
    assert m and m[1]==word,(pc,word)
    ins=m[2].strip(); guest=bool(re.match(r'(?:ngb_reg_)?(?:sub_|d3d_orig_)',name))
    if name.startswith('ngb_gate_') or name in ('ngb_reg_checkpoint','ngb_checkpoint'):group='ABI gate/checkpoint'
    elif name in {'execute_dma','service_dma','submit_dma','ngb_poll_due','yield_worker','poll_callbacks'}:group='service body'
    elif name in {'ngb_guest_pointer','ngb_guest_scalar_fallback','ngb_ram_span'}:group='memory helper'
    elif guest:
        if re.search(r'\[x27,',ins) and name.startswith('ngb_reg_'):group='guest page-table load'
        elif re.search(r'/guest_memory\.h:(59|60)(?: |$)',source[pc]):group='guest memory header (debug line)'
        elif re.search(r'^and\s+x(\d+), x\1, #0x7fffffff$',ins) and re.search(r'add\s+x\d+, x26, x\d+',raw) and name.startswith('ngb_reg_'):group='guest RAM alias translation'
        elif re.search(r'^stp\s+x29, x30, \[sp, #-',ins):group='guest ARM frame prologue'
        elif re.search(r'<(?:ngb_reg_checkpoint|ngb_gate_\w+)>',ins):group='guest branch to gate/checkpoint'
        elif re.search(r'<(?:ngb_guest_polls|ngb_poll_mask|ngb_pending_dpcs)>',ins):group='guest poll symbol'
        else:group='guest instructions, unattributed'
    elif name in {'memcmp','memcpy','memset','memmove'}:group='byte compare/copy/set'
    elif name.startswith('0x'):group='system call' if ins.startswith('svc') else 'unsymbolized'
    else:group='other native'
    if group in ('guest page-table load','guest RAM alias translation','guest memory header (debug line)','memory helper'):
        st=[sym(p).removeprefix('ngb_reg_') for p in pcs]
        task=next((s for s in st if s in {'sub_001CA790','sub_001CB9A0','sub_000320E0'}),'other')
        tasks[task]+=1
    counts[group]+=1; detail.append((frame,worker,hex(pc),name,group,ins,source[pc]))
print('ELF build ID',bid,'samples',sum(counts.values()))
for k,n in counts.most_common():print(n,k)
print('memory samples by enclosing task:', dict(tasks))
if '--details' in sys.argv:
 for r in detail:print(*r,sep='\t')
