"""Split the effect of relocating the public wrappers from bypassing them."""
from pathlib import Path
import os,shutil,struct,subprocess as sp,tempfile
d=Path('build/switch-runtime/core-perf/wide-start').resolve()
p=Path(__file__).resolve().parent
fast=d/'limit'
def disable(buf,offset):
 # Check both conditional exits, the jump to the private slot, and the
 # expected first instruction of the conservative public ABI path.
 w=struct.unpack_from('<16I',buf,offset)
 def bcond(i,cond):
  assert w[i]&0xff00001f==0x54000000|cond
  imm=(w[i]>>5)&0x7ffff;return i+(imm if imm<0x40000 else imm-0x80000)
 target=bcond(4,1)
 assert target==bcond(8,2)==11 and w[10]==0xd61f0200 and w[target]==0xa9bf7bfd
 assert w[0]&0x9f00001f==0x90000011
 struct.pack_into('<I',buf,offset,0x14000000|target)
def control(exe):
 import mmap
 symbols=sp.check_output(['nm','-n',exe],text=True).splitlines()
 sym={l.split()[-1]:int(l.split()[0],16) for l in symbols if len(l.split())==3}
 assert 'ngb_slot_start' in sym
 pc=sym['ngb_gate_indirect']
 with exe.open('r+b') as f,mmap.mmap(f.fileno(),0) as buf:
  assert buf[:6]==b'\x7fELF\x02\x01'
  u=lambda fmt,o:struct.unpack_from('<'+fmt,buf,o)
  ph=[u('IIQQQQQQ',u('Q',32)[0]+i*u('H',54)[0]) for i in range(u('H',56)[0])]
  seg,=[x for x in ph if x[0]==1 and x[1]&1 and x[3]<=pc<pc+64<=x[3]+x[5]]
  disable(buf,pc-seg[3]+seg[2])
with tempfile.TemporaryDirectory(prefix='slot-control-',dir=d) as tmp:
 slow=Path(tmp)/'control';shutil.copy2(fast,slow);control(slow)
 for arm in ('original-1','limit-1','limit-2','original-2','original-3','limit-3','limit-4','original-4'):
  env=dict(os.environ,NGB_OPEN_REPLAY=str(slow if arm.startswith('original') else fast))
  sp.run(['sh',p/'run-wide.sh','slot-layout-control-'+arm],env=env,check=True)
for report in ('page-limit-report.py','work-match.py'):
 sp.run(['python3',p/report,d,'slot-layout-control'],check=True)
