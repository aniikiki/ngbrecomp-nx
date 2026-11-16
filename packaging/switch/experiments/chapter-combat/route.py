"""Follow the observed first-chapter ledges with hysteresis: remember a fall
until back at the ramp. Never aim at the isolated ledge from the pit floor."""
import sys,re,time
from pathlib import Path
log,pad=map(Path,sys.argv[1:3]);stage='recover';stable=0;prev=None;start=0
pattern=re.compile(r'\[FIGHT\] (\d+) stage=\d+ pos=([-.\d]+),([-.\d]+),([-.\d]+) target=(\d+) at=([-.\d]+),([-.\d]+),([-.\d]+)')
with log.open() as f:
 f.seek(0,2)
 while True:
  l=f.readline()
  if not l:time.sleep(.035);continue
  if '[RESULT]' in l:break
  m=pattern.match(l)
  if not m:continue
  t,x,y,z,en,ex,ey,ez=map(float,m.groups())
  if y<-4 and stage!='recover':stage='recover';start=t
  if stage=='recover':
   cmd='2 1450 -175 48 4 256' if t-start<180 else '2 2020 700 51 5 256'
   if t-start>380:start=t
   if x<17 and z<2 and y>=-2:stage='ramp'
   if x<19 and z>=2:cmd='2 1000 80 52 4 256'
  if stage=='ramp':
   cmd='1 17000 26800 42 4 256'
   if x>19 and y>0.5:stage='cross'
  if stage=='cross':
   cmd='2 2950 -450 52 4 256'
   if 4.46<=y<=4.52 and x>26:stable+=1
   else:stable=0
   if stable>=2:stage='shimmy';start=t
  if stage=='shimmy':
   cmd='1 -32000 0 60 0 0'
   if t-start>=90:stage='up';start=t
  if stage=='up':
   cmd='1 0 0 48 5 256'
   if t-start>=60:stage='next';start=t
  if stage=='next':
   cmd='2 2780 -1420 46 4 256'
   if y>12:stage='tree'
   elif t-start>490 and y<5:stage='cross';stable=0
  if stage=='tree':
   cmd='2 2680 -1680 48 4 256'
   if y>16:stage='battle'
  if stage=='battle':
   cmd=f'2 {round(ex*100)} {round(ez*100)} 13 4 1024' if en and abs(ey-y)<2 else '2 2370 -1950 45 3 256'
  if stage!=prev:print(int(t),stage,(x,y,z),flush=True);prev=stage
  tmp=pad.with_suffix('.new');tmp.write_text(cmd+'\n');tmp.replace(pad)
