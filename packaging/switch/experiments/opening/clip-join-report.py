"""Join strictly by command ID. Cached-box replay is an offline hypothesis, not an early visibility implementation."""
from pathlib import Path
from collections import Counter
from itertools import product
from struct import Struct,unpack
import sys
d=Path(sys.argv[1]);log=(d/'joined.log').read_text()
assert '[JOIN] original opening motion verified at 120' in log and '[RESULT] status=1 reason=finished joined opening' in log
pr=list(Struct('<6I192s').iter_unpack((d/'producer.bin').read_bytes()))
dr=list(Struct('<2I192s16f6f').iter_unpack((d/'draw.bin').read_bytes()))
draw={a[0]:a[1:] for a in dr}
assert len(draw)==len(dr) and set(draw)=={r[0] for r in pr if r[4]} and all(r[4]<=1 for r in pr)
assert [r[0] for r in pr]==list(range(1,len(pr)+1)) and set(r[1] for r in pr)==set(range(1,121))
ep=d/'entry.bin';entry={} if not ep.exists() else {r[0]:r[1:] for r in Struct('<I16f').iter_unpack(ep.read_bytes())}
assert not entry or set(entry)=={r[0] for r in pr}
# Upper bound with previous-frame observations; no result from the current frame informs its decisions.
prior={};pending={};prevf=0
cache={};rows=[]
def outside(box,m):
 tol=(1+sum(max(abs(box[i]),abs(box[i+3])) for i in range(3)))*max(map(abs,m))*2e-5+1e-4
 for axis,sign in ((0,1),(0,-1),(4,1),(4,-1)):
  c=[m[12+i]+sign*m[axis+i] for i in range(4)]
  if sum(max(box[i]*c[i],box[i+3]*c[i]) for i in range(3))+c[3] < -tol:return True
 return False
for seq,f,key,pc,n,ns,pm in pr:
 if prevf!=f:prior.update(pending);pending={};prevf=f
 k=(pc,key)
 # Importantly, predict without consulting whether this draw is eligible at the backend.
 guess=bool(entry and k in prior and prior[k] and outside(prior[k],entry[seq]))
 if not n:
  rows.append((f,Counter(total=1,total_ns=ns,empty=1,early_false=int(guess))));pending[k]=None;continue
 stage,rm,*v=draw[seq];m=v[:16];box=tuple(v[16:]);cut=bool(stage&2)
 r=Counter(total=1,total_ns=ns,cut=int(cut),cut_ns=ns*cut)
 if entry:
  r['early_guess']+=guess;r['early_true']+=guess and cut;r['early_false']+=guess and not cut;r['false_ineligible']+=guess and not(stage&4);r['false_eligible']+=guess and bool(stage&4) and not cut;r['early_ns']+=ns*(guess and cut)
  if stage&4:r['early_clip_equal']+=entry[seq]==tuple(m)
 pending[k]=box if stage&4 else None
 if stage&4:
  same=rm==pm;r['matrix_same']+=same;r['eligible']+=1
  valid=outside(box,m)
  if valid and not cut:raise ValueError('actual-bounds prediction rejected by vertex reference')
  r['actual_box']+=valid
  old=cache.get(key)
  if old is not None and same:
   pred=outside(old,m)
   r['observed_stable_bounds']+=old==box
   r['available_prior']+=1
   r['candidate']+=pred;r['false']+=pred and not cut;r['candidate_cut_ns']+=ns*(pred and cut)
  cache[key]=box
 rows.append((f,r))
for lo,hi in [(1,120),(31,120)]:
 u=sum((r for f,r in rows if lo<=f<=hi),Counter())
 print(lo,hi,dict(u),'ms/frame all/culled/candidate',*[round(u[k]/((hi-lo+1)*1e6),4) for k in ('total_ns','cut_ns','candidate_cut_ns')])
