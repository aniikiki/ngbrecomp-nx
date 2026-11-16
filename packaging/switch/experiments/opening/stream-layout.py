"""Cluster compact guest bodies from observed temporal transitions (not static calls)."""
import re
from collections import Counter
def script(base,out):
 d=base/'core-perf'
 s=(d/'opening-entry-stream/budget.log').read_text()
 assert 'verified 120 original demo frames' in s
 totals=re.findall(r'^\[STREAM_TOTAL\] (\d+) .*?dropped=(\d+)$',s,re.M)
 assert totals==[('30','0'),('120','0')],totals
 sy={}
 for row in (d/'opening-compact-profile/symbols.txt').read_text().splitlines():
  a,n,_,fn=row.split(maxsplit=3)
  if re.fullmatch('ngb_reg_sub_[0-9A-F]+',fn):sy[int(fn[12:],16)]=(int(a,16),int(n,16),fn[8:])
 weight=Counter()
 for _,a,b,n in re.findall(r'^\[STREAM_EDGE\] (\d+) (\w+) (\w+) (\d+)$',s,re.M):
  a,b=int(a,16),int(b,16)
  if a!=b and a in sy and b in sy:weight[min(a,b),max(a,b)]+=int(n)
 assert weight
 # Pack high-frequency pairs into up to one 4 KiB page per cluster; bound
 # the number of clusters and changed layout. Large functions remain alone.
 clusters={};owner={}
 for (a,b),w in weight.most_common():
  if w<120:break
  x,y=owner.get(a,a),owner.get(b,b)
  if x==y:continue
  l=clusters.get(x,[a]);r=clusters.get(y,[b])
  if sum((sy[i][1]+31)&~31 for i in l+r)>4000:continue
  if len(l)==1 and len(r)==1 and len(clusters)>=32:continue
  clusters[x]=l+r;clusters.pop(y,None)
  for v in r+l:owner[v]=x
 assert clusters
 lines=['SECTIONS { .text.ngb_opening ALIGN(4096) : {']
 for vs in clusters.values():
  lines.append(' . = ALIGN(4096);')
  lines.extend(' *recomp_*.c.o(.text.'+sy[v][2]+')' for v in vs)
 lines.append('} } INSERT BEFORE .text;')
 out.write_text('\n'.join(lines)+'\n')
 links=sum(n for (a,b),n in weight.items() if a in owner and owner[a]==owner.get(b))
 already=sum(n for (a,b),n in weight.items() if a in owner and owner[a]==owner.get(b) and sy[a][0]//4096==sy[b][0]//4096)
 print('formerly on different entry pages (subset)',links-already,flush=True)
 print('stream page clusters',len(clusters),'functions',len(owner),'intra-cluster transitions',links,'of eligible distinct-end transitions',sum(weight.values()),flush=True)
