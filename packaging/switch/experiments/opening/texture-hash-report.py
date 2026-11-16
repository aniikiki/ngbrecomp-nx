"""Validate present order and summarize render-thread signature counters."""
from pathlib import Path
import sys,re
s=Path(sys.argv[1]).read_text()
assert '[HASH_WINDOW] guest reached 120 with motion' in s and '[RESULT] status=1 reason=completed hash diagnostic' in s
rows=[list(map(int,l.split()[1:])) for l in s.splitlines() if l.startswith('[HASHFRAME]')]
assert [r[0] for r in rows]==list(range(1,121))
for start in (1,31):
 window=rows[start-1:];n=len(window)
 hits,body,bytes_,ns,known,same,adj,sbytes,sns,pal,pns,cal=map(sum,zip(*(r[1:] for r in window)))
 assert 0<=adj<=same<=known<=body and sbytes<=bytes_ and sns<=ns
 overhead=cal/(body+pal) if body+pal else 0
 print(f'{start}..120: same-frame memo hits={hits} full_hashes={body} previous={known} same_signature={same} adjacent_frame_same={adj} P8={pal}')
 for name,total in [('all_bytes',bytes_),('same_bytes',sbytes),('P8_bytes',pal*1024)]:
  print(name,total,'MiB/frame',round(total/1048576/n,4))
 for name,t,c in [('body',ns,body),('same',sns,same),('palette',pns,pal)]:
  print(name,'raw / clock-adjusted render CPU ms/frame',round(t/1e6/n,5),round(max(0,t-c*overhead)/1e6/n,5))
 print('empty clock pair ns',round(overhead,1))
