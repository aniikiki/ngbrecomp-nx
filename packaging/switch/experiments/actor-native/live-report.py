"""Report only work adopted by an original 1920-flip combat replay."""
from pathlib import Path
import re,sys,statistics
s=Path(sys.argv[1]).read_text()
def records(tag):
 return [{k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',l)} for l in s.splitlines() if l.startswith('['+tag+']')]
jobs=records('LIVE_REPLACED');compact=records('COMPACT_LIVE')
if not jobs or 'reason=verified original combat window' not in s:sys.exit('no confirmed replacement or incomplete combat replay')
if [p['total'] for p in jobs]!=list(range(1,len(jobs)+1)):sys.exit('discontinuous replacement sequence')
print('live adopted:',len(jobs),'actor jobs,',sum(p['events'] for p in jobs),'polls,',sum(p['entries'] for p in jobs),'guest function entries;',sorted({p['actor'] for p in jobs}))
if compact:
 if len(compact)!=len(jobs):sys.exit('missing compact record')
 print('poll services:',sum(p['served'] for p in compact),'raw byte writes:',sum(p['raw_bytes'] for p in compact),'masked words:',sum(p['masked_words'] for p in compact),'prepared blocks:',sum(p.get('prepared',0) for p in compact))
cost=records('PUBLICATION_COST')
for i in sorted({p['actor'] for p in cost}):
 print('actor',i,'reference/publish-only us',[(len(v),round(statistics.median(v)/1000,2)) if v else None for v in ([p['ns'] for p in cost if p['actor']==i and p['replay']==m] for m in (0,1))])
