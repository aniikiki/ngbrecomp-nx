"""ABBA whole-frame comparison. Inputs: frames.csv produced by instrument.py."""
import csv,sys,statistics as st,collections
with open(sys.argv[1]) as fh:
 rows=[list(map(int,x)) for x in csv.reader(fh) if len(x)==13]
Y=[x for x in rows if 0<x[1]<2400 and sum(x[3:6])>300];groups=collections.defaultdict(list)
for x in Y:groups[x[0]//32].append(x)
for b in (0,1):
 g=[x for x in Y if x[2]==b]
 if not g:continue
 print(('original','native')[b], 'frames',len(g),'indexed,linear,up,old-eligible,new-eligible,new-indices,linear-taken,compact-actually-taken',*[sum(x[i] for x in g) for i in range(3,11)],'median frame CPU/wall ms',*[round(st.median(x[i] for x in g)/1e6,3) for i in (11,12)])
pairs=[];blocks=[]
for group in groups.values():
 a=[r for r in group if not r[2]];b=[r for r in group if r[2]]
 if len(a)==len(b)==16:
  blocks.append([(st.mean(x[j] for x in a)-st.mean(x[j] for x in b))/1e6 for j in (11,12)])
 for x in a:
  others=[y for y in b if x[1]==y[1] and sum(abs(x[j]-y[j]) for j in (3,4,5))<=12]
  if not others:continue
  y=min(others,key=lambda y:(sum(abs(x[j]-y[j]) for j in (3,4,5)),abs(x[0]-y[0])))
  b.remove(y);pairs.append([(x[j]-y[j])/1e6 for j in (11,12)])
for k,g in [('32-frame ABBA blocks',blocks),('nearby same-HP matched frames',pairs)]:
 if g:print(k,len(g),'CPU A-B mean/median, wins',round(st.mean(x[0] for x in g),3),round(st.median(x[0] for x in g),3),sum(x[0]>0 for x in g),'wall A-B mean/median',round(st.mean(x[1] for x in g),3),round(st.median(x[1] for x in g),3))
