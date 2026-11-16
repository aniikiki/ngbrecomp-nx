"""Require complete real replay windows; differentiate dependency counts from time."""
import argparse,re
from pathlib import Path
from collections import Counter
from bisect import bisect_right
ap=argparse.ArgumentParser(description=__doc__)
for a in ('strict','raw','versions','symbols'):ap.add_argument(a,type=Path)
args=ap.parse_args()
def lines(p):
 s=p.read_text();assert '[RESULT] status=1 reason=verified original combat window' in s,p
 return s.splitlines()
def windows(p,tag):
 out={int(t[1]):t for l in lines(p) if (t:=l.split()) and t[0]==tag}
 assert sorted(out)==list(range(1801,1813)),(p,sorted(out))
 return out
strict=windows(args.strict,'[FLOW_PATH]');raw=windows(args.raw,'[RAW_PATH]');versions=windows(args.versions,'[VERSIONS]')
work=chain=raw_work=raw_chain=0
for f in strict:
 a=[tuple(map(int,x.split(':'))) for x in strict[f][3:]]
 assert sorted(i for i,_,_ in a)==list(range(1,6))
 work+=sum(w for _,w,_ in a);chain+=max(e for _,_,e in a)
 row=dict(x.split('=') for x in raw[f][2:]);raw_work+=int(row['total']);raw_chain+=int(row['critical'])
print(f'Ordered accesses: {chain:,} / {work:,}. Changed-byte RAW: {raw_chain:,} / {raw_work:,}. Different runs.')
symbols={}
for l in args.symbols.open():
 m=re.fullmatch(r'([0-9a-fA-F]+) [tTwW] (.+)\n',l)
 if m:symbols[int(m[1],16)]=m[2]
a=sorted(symbols)
def name(s):return symbols[a[bisect_right(a,int(s,16)-4)-1]].removeprefix('alt_')
hops=Counter();length=Counter()
for l in lines(args.raw):
 t=l.split()
 if not t or t[0] not in ('[RAW_HOP]','[RAW_ROOT]'):continue
 f=int(t[1]);d=dict(x.split('=') for x in t[2:]);length[f]+=int(d['length'])
 if t[0]=='[RAW_HOP]':hops[(d['at'],name(d['write']),name(d['read']))]+=1
for f in raw:assert length[f]==int(raw[f][3].split('=')[1]),f
for item,n in hops.most_common():print(n,*item)
totals=[sum(int(t[4+i].split(':')[0]) for t in versions.values()) for i in range(4)]
assert all(n<=totals[0] for n in totals[1:])
print('Same replay: observed changed-byte producing writes, matrix history, initial values, all historical bytes:')
for v in totals:print(v,round(v/totals[0],4))
