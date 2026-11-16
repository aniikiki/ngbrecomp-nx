"""Attribute true hardware ring retirement vs the remaining wall budget. Per
frame timing inside the guest FIFO is inclusive wall time, not additive CPU."""
import re
from pathlib import Path
base=Path('build/switch-runtime/device-logs')
s=next(base.glob('0.55.0-wide-*/boot.log')).read_text()
s=s[:s.index('3D scene flips=240')]
windows=[]
for part in s.split('3D scene window frames=')[1:3]:
 result={}
 for k in ('fifo_ms','fifo_batched_words','elapsed_ms','draws'):
  if k in ('elapsed_ms','draws'):
   m=re.search(r'3D scene flips=\d+ draws=(\d+) elapsed_ms=(\d+)',part);result[k]=int(m[1 if k=='draws' else 2])
  else:result[k]=int(re.search(r'\b'+k+r'=(\d+)',part)[1])
 windows.append(result)
a,b=windows
for k in a:print(k,'delta',b[k]-a[k],'per flip',(b[k]-a[k])/90)
