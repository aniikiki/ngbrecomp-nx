"""Count direct x28-relative XMM file accesses at exclusive PCs (no caller attribution)."""
from pathlib import Path
from collections import Counter
import contextlib,io,runpy,json,re,hashlib,subprocess,tempfile
p=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
 q=runpy.run_path(str(p/'compact-entry-edges.py'))
base=Path('build/switch-runtime'); h=base/'history/0.51.0-rc1'
dep=json.loads((h/'deployment.json').read_text()); nro=(h/'ngb-startup.nro').read_bytes()
assert hashlib.sha256(nro).hexdigest()==dep['sha256']
api=runpy.run_path(str(p.parents[1]/'analyze-profile.py'));sym=api['load_symbols'](h/'symbols.gz')
win=api['parse_windows']((base/dep['hardware_log']).read_text().splitlines())[1,120]
host=[(fn,q['code'][fn][o:o+4]) for (fn,o),_ in q['samples']]
hw=[(sym(pcs[0]),nro[pcs[0]:pcs[0]+4]) for f,_,_,_,_,pcs in win['profiles']['guest'][1] if 31<=f<=120 and sym(pcs[0]).startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_'))]
def audit(name,rows):
 with tempfile.TemporaryDirectory() as t:
  f=Path(t)/'insns';f.write_bytes(b''.join(v for _,v in rows))
  out=subprocess.check_output(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objdump','-D','-z','-b','binary','-m','aarch64',f],text=True)
 ops=re.findall(r'^\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(\S+)\s*([^\n]*)',out,re.M)
 assert len(ops)==len(rows)
 c=Counter()
 for i,(a,ins,args) in enumerate(ops):
  assert int(a,16)==4*i
  m=re.fullmatch(r'(\w+)(?:, (\w+))?, \[x28(?:, #(-?\d+))?\]',args.strip())
  if not m or not ins.startswith(('ld','st')):continue
  off=int(m[3] or 0)
  if 120<=off<248:c['XMM reads' if ins.startswith('ld') else 'XMM writes']+=1
  else:c['other regfile']+=1
 print(name,len(rows),dict(c))
audit('host',host);audit('device old build',hw)
