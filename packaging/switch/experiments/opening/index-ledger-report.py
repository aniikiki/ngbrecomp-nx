"""Summarize both measurement designs; never rescale host times to Switch."""
from pathlib import Path
import re,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/switch-runtime/core-perf')
def rows(d,tag):
 s=(root/d/'indexed.log').read_text();assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
 rr=[l.split()[1:] for l in s.splitlines() if l.startswith('['+tag+']')];assert [x[0] for x in rr]==['30','120'];return rr
ledger=rows('opening-index-ledger','INDEX_LEDGER')
single=rows('opening-index-single','IX_SINGLE')
for x,y,n in zip(ledger,single,[30,90]):
 f,hz,c,nsamp,nest,cross,total=map(int,x[:7]);t=list(map(int,x[7:17]));assert sum(t)==total and not(nest or cross)
 _,hz2,c2,bad=map(int,y[:4]);a=[tuple(map(int,i.split(':'))) for i in y[4:]];assert not bad and sum(v[0] for v in a)==c2
 # 0 is entered twice in the common path; apply two empty-span corrections to its single-span estimate.
 us=lambda v:round(v*1e6/hz,3)
 print('window end',f,'calls/frame',c/n,c2/n,'ledger samples',nsamp,'clock pair us',us(int(x[-1].split('=')[1])/1024))
 empty=a[11][1]/a[11][0];print('single-span control us',round(empty*1e6/hz2,3))
 for i,label in enumerate('hook sync lock headers peek fixed constants indices enqueue XDK'.split()):
  print(label,'ledger %',round(100*t[i]/total,1),'single raw us/call',round(a[i][1]/a[i][0]*1e6/hz2,3),'single adjusted ms/frame',round(max(0,a[i][1]/a[i][0]-empty*(2 if i==0 else 1))/hz2*1000*c2/n,4))
 print('whole call single adjusted ms/frame',round((a[10][1]/a[10][0]-empty)/hz2*1000*c2/n,4))
