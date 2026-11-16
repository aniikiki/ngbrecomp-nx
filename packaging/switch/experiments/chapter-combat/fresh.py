"""First chapter replay from a fresh temporary HDD. Use the original fixed
ramp input and switch to observed world-space targets after climbing the ramp."""
import sys,re,time
from pathlib import Path
log,pad=map(Path,sys.argv[1:3]);state='cross';prev=0;stable=0;epoch=0
while not log.exists():time.sleep(.2)
with log.open() as f:
 while True:
  s=f.readline()
  if not s:time.sleep(.03);continue
  if '[RESULT]' in s:break
  m=re.match(r'^\[FIGHT\] (\d+) stage=(\d+) pos=([-.\d]+),([-.\d]+),([-.\d]+) target=(\d+) at=([-.\d]+),([-.\d]+),([-.\d]+)',s)
  if not m:continue
  t,stage,x,y,z,en,ex,ey,ez=map(float,m.groups())
  if stage<2:continue
  old=state
  if state=='cross':
   cmd='2 2950 -450 52 4 256'
   stable=stable+1 if 4.47<=y<=4.53 and x>26.8 else 0
   if stable>=2:state='pull';epoch=t
  elif state=='pull':
   cmd='1 0 0 100 5 256'
   if t-epoch>=48:state='walk';epoch=t
  elif state=='walk':
   cmd='2 2780 -1420 48 4 256'
   if y>=12:state='tree'
   elif y<1:state='cross';stable=0
  elif state=='tree':
   cmd='2 2680 -1680 45 4 256'
   if y>16:state='encounter'
  else:
   cmd=f'2 {round(ex*100)} {round(ez*100)} 13 5 1024' if en and abs(ey-y)<2.2 else '2 2440 -1940 48 4 256'
  if old!=state:print(int(t),old,state,x,y,z,flush=True)
  tmp=pad.with_suffix('.part');tmp.write_text(cmd+'\n');tmp.replace(pad)
