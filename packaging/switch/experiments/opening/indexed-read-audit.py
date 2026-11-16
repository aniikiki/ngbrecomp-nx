"""Count actual single indexed LDR encodings in executable sections, not text substitutions."""
import re,struct,runpy,sys
from pathlib import Path
p=Path(__file__).parent;root=Path('build/switch-runtime')
change=runpy.run_path(str(p/'indexed-read.py'))['line']
def analyze(obj):
 b=obj.read_bytes();assert b[:6]==b'\x7fELF\x02\x01'
 off=struct.unpack_from('<Q',b,40)[0];step,n=struct.unpack_from('<HH',b,58)
 hits=size=0
 for i in range(n):
  _,kind,flags,_,pos,length,*_=struct.unpack_from('<IIQQQQIIQQ',b,off+i*step)
  if kind!=1 or not flags&4:continue
  size+=length
  for w, in struct.iter_unpack('<I',b[pos:pos+(length&~3)]):
   hits+=w&0xffe0ffe0==0xb8604b40
 return hits,size
allcounts=[0]*5
for u in (2,10,16,26,39):
 n=f'recomp_{u:04}.c';counts=[len(change.findall((root/'gen'/n).read_text()))]
 for g in ('compact-loops','indexed-read'):
  counts.extend(analyze(root/'core-perf'/('opening-'+g)/(n+'.o')))
 print(u,'sites, baseline indexed LDR/text bytes, candidate indexed LDR/text bytes:',*counts)
 allcounts=[x+y for x,y in zip(allcounts,counts)]
print('total',*allcounts);assert allcounts[3]>allcounts[1]
