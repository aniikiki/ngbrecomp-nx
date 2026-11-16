"""Join sampled guest function offsets to the retained baseline; classify store patterns only."""
from pathlib import Path
import bisect,re,struct
from collections import Counter
d=Path('build/switch-runtime/core-perf');p=d/'opening-copy-profile'
buf=(d/'wide-start/replay').read_bytes()
def un(fmt,i):return struct.unpack_from('<'+fmt,buf,i)
sh=[un('IIQQQQIIQQ',un('Q',40)[0]+64*i) for i in range(un('H',60)[0])]
sym={}
for s in sh:
 if s[1]!=2:continue
 strings=sh[s[6]][4]
 for pos in range(s[4],s[4]+s[5],24):
  k,info,_,ndx,a,n=un('IBBHQQ',pos)
  if not ndx or not n:continue
  name=buf[strings+k:buf.index(b'\0',strings+k)].decode()
  sym[name]=a,n,ndx
sy={}
for l in (p/'symbols.txt').read_text().splitlines():
 a,n,_,name=l.split(maxsplit=3);a,n=int(a,16),int(n,16)
 if n>sy.get(a,(0,''))[0]:sy[a]=(n,name)
keys=sorted(sy);counts=Counter()
def store(w):
 if w&0xffc00000!=0xb9000000:return None
 return (w&31,(w>>5)&31,4*((w>>10)&4095))
for i in range(1,5):
 s=(p/f'run-{i}.log').read_text();assert 'reason=verified 120 original demo frames' in s
 for f,pc in re.findall(r'^\[FRAME_PC\] (\d+) (\w+)$',s,re.M):
  phase=int(f)>30;pc=int(pc,16);j=bisect.bisect_right(keys,pc)-1
  if j<0:continue
  a=keys[j];n,name=sy[a];off=pc-a
  if off>=n or not name.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):continue
  counts[phase,'guest']+=1
  assert name in sym and sym[name][1]==n,(name,n,sym.get(name))
  base,_,idx=sym[name];sec=sh[idx];at=base+off-sec[3]+sec[4];v=store(un('I',at)[0])
  if v is None or v[2] not in (28,36):continue
  counts[phase,'single offset']+=1
  for step in (-4,4):
   if not 0<=off+step<n:continue
   other=store(un('I',at+step)[0])
   if other and other[:2]==v[:2] and {v[2],other[2]}=={28,36}:
    counts[phase,'adjacent pair']+=1
    if v[1]==28:counts[phase,'x28 confirmed']+=1
    break
for phase in (False,True):
 print('31..120' if phase else '1..30', {k:counts[phase,k] for k in ('guest','single offset','adjacent pair','x28 confirmed')})
