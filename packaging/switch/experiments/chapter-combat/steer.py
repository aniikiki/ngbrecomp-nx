"""Steer the live USB probe by observed positions; write only its private pad
file. Each stage is bounded. No game RAM or save is modified by this script."""
from pathlib import Path
import re,time,sys
log,pad=map(Path,sys.argv[1:3]);stage=0;began=0;ever=False;previous_surface=0
pat=re.compile(r'^\[FIGHT\] (\d+) stage=\d+ pos=([-.\d]+),([-.\d]+),([-.\d]+) target=(\d+) at=([-.\d]+),([-.\d]+),([-.\d]+)')
with log.open() as stream:
 stream.seek(0,2)
 while True:
  l=stream.readline()
  if not l:time.sleep(.04);continue
  if '[RESULT]' in l:break
  m=pat.match(l)
  if not m:continue
  t,x,y,z,enemy,ex,ey,ez=map(float,m.groups());t=int(t)
  if y<1:stage=0
  if y>8:stage=3
  if y>13.4:stage=4
  if y>16.3:stage=5
  if stage==0:
   cmd='2 2950 -450 52 4 256'
   if y>=4.44 and 27<x<32 and t-previous_surface>=24:stage=1;began=t
   if y<4.42 or y>4.51:previous_surface=t
   if y<0 and x>26:cmd='2 1800 -250 68 0 0'
  if stage==1:
   # Climb from a hang. Holding a stick longer runs off the far edge.
   cmd='2 2780 -1420 39 3 256'
   if t-began>=48 or x>31.2:stage=2;began=t
  if stage==2:
   cmd='2 2780 -1420 42 4 256'
   if t-began>220 and y<5 and abs(x-30)<2:stage=1;began=t
  if stage==3:cmd='2 2780 -1420 44 4 256'
  if stage==4:cmd='2 2680 -1680 44 4 256'
  if stage==5:cmd=f'2 {int(ex*100)} {int(ez*100)} 16 5 1024' if enemy and abs(ey-y)<2 else '2 2300 -1950 42 4 256'
  tmp=pad.with_suffix('.new');tmp.write_text(cmd+'\n');tmp.replace(pad)
