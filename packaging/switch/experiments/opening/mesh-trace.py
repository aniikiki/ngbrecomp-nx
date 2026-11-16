"""Linearize the most prevalent observed trace. On the first divergence resume the original block, never restart a submission."""
from pathlib import Path
import re,runpy
def transform(s,u):
 log=Path('build/switch-runtime/core-perf/opening-mesh-paths/budget.log').read_text()
 rows=[(int(a),int(b),bytes.fromhex(p)) for a,b,p in re.findall(r'^\[MP_PATH\] (\d+) (\d+) ([0-9a-f]+)$',log,re.M)]
 trace=max(rows,key=lambda r:r[0])[2]
 head='void sub_0030BCA0(void)\n{';a=s.index(head);b=s.index('\n}',a);body=s[a:b]
 blocks=re.split(r'(?m)(?=^loc_\w+: ;)',body)[1:]
 labels=[v.split(':',1)[0] for v in blocks];assert len(labels)==88
 # Share the real epilogue, including removal of local preprocessor macros.
 assert trace[0]==0 and trace[-1]==87
 linear=[];plan={}
 cond=re.compile(r'(?m)^    if \(([^\n]+)\) goto (loc_\w+);[^\n]*$')
 for i,nxt in zip(trace,trace[1:]):
  text=blocks[i].split(': ;',1)[1]
  assert not re.search(r'(?m)^\s*(?:static\b|#)|\breturn\b',text)
  if 'goto ' in text:
   m=cond.search(text);assert m and text.count('goto ')==1
   target=labels.index(m[2]);other=i+1
   assert nxt in (target,other) and other!=target
   inverse=nxt==target;side=other if inverse else target
   condition='!('+m[1]+')' if inverse else m[1]
   text=text[:m.start()]+f'    if (__builtin_expect(!!({condition}),0)) goto {labels[side]};'+text[m.end():]
   plan[i]=(nxt,side,target,other)
  else:
   assert nxt==i+1;plan[i]=(nxt,None,None,None)
  linear.append(text)
 # Verify both possible next blocks at every cloned conditional and simulate
 # all captured paths, including deterministic exits to the uncommon graph.
 for i,(n,side,t,f) in plan.items():
  if side is not None:
   for taken in (False,True):
    actual=t if taken else f
    assert (side if (not taken if n==t else taken) else n)==actual
 for _,_,p in rows:
  for i,n in zip(p,p[1:]):
   hot,side,*_=plan[i]
   if n==side:break
   assert n==hot
 k='loc_0030BCA0: ;';assert body.count(k)==1
 body=body.replace(k,''.join(linear)+'\n    goto '+labels[87]+';\n'+k)
 body=body.replace(head,'__attribute__((optimize("no-crossjumping,no-tree-tail-merge"))) '+head)
 return s[:a]+body+s[b:]
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('mesh-trace',[(False,[28])],transform)
