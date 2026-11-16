"""Inline the observed 3B420 -> 3AE90 edge, preserving the original guest stack and polls."""
from pathlib import Path
import runpy
def transform(s,u):
 head='void sub_0003AE90(void)\n{'
 a=s.index(head);b=s.index('\n}',a)+2
 dup=s[a:b].replace(head,'static __attribute__((always_inline)) inline void pred_edge_child(void)\n{',1)
 call='RECOMP_ABI_CALL(0x0003AE90u, sub_0003AE90)'
 beg=s.index('void sub_0003B420(void)\n{');end=s.index('\n}',beg)+2
 assert s[beg:end].count(call)==1 and b<beg
 return s[:beg]+dup+'\n'+s[beg:end].replace(call,call.replace('sub_0003AE90','pred_edge_child'))+s[end:]
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('predicate-edge',[(True,[2])],transform)
