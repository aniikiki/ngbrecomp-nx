"""Compare exact generated body sizes and relocation sites. Static counts, never cycles."""
import re,struct,subprocess as sp,sys
from pathlib import Path
root=Path('build/switch-runtime/core-perf')
tool=sp.check_output(['xcrun','-f','llvm-nm'],text=True).strip()
tag=sys.argv[1]; units={'stack-long-run':[1,9,15],'stack-prefix':[2,10,16,26,39],'stack-outline':[2,10,16,26,39],'call-stack':[2,16,0,28,29]}[tag]
def symbols(folder,n):
 out=sp.check_output([tool,'-S','--defined-only',str(root/folder/f'recomp_{n:04}.c.o')],text=True)
 return {fn:int(sz,16) for sz,fn in re.findall(r'^[\da-f]+ ([\da-f]+) [Tt] (ngb_reg_(?:sub_|d3d_orig_)[0-9A-F]+)$',out,re.M)}
def exec_bytes(folder,n):
 # Unlinked ELF section headers: count each executable section once. Includes
 # split .cold clones and out-of-line helpers even if absent from the public symbols.
 b=(root/folder/f'recomp_{n:04}.c.o').read_bytes()
 assert b[:6]==b'\x7fELF\x02\x01'
 f=struct.Struct('<IIQQQQIIQQ')
 off=struct.unpack_from('<Q',b,40)[0];step,nsec=struct.unpack_from('<HH',b,58)
 assert step==f.size and nsec
 sizes=[h[5] for i in range(nsec) if (h:=f.unpack_from(b,off+i*step))[2]&4 and h[1]==1]
 assert sizes
 return sum(sizes)
old=new=changed=larger=smaller=oldtext=newtext=0
for i in units:
 a=symbols('opening-compact-loops' if i in (2,10,16,26,39) else 'opening-full-page',i);b=symbols('opening-'+tag,i);assert a and a.keys()==b.keys()
 oldtext+=exec_bytes('opening-compact-loops' if i in (2,10,16,26,39) else 'opening-full-page',i);newtext+=exec_bytes('opening-'+tag,i)
 old+=sum(a.values());new+=sum(b.values())
 for n in a:
  if a[n]!=b[n]:changed+=1;larger+=a[n]<b[n];smaller+=a[n]>b[n]
print(tag,'bytes',old,'->',new,'delta %.2f%%'%(100*(new/old-1)),'changed sizes',changed,'larger',larger,'smaller',smaller)

print('all executable sections',oldtext,'->',newtext, 'delta %.2f%%'%(100*(newtext/oldtext-1)))
if '--gate' in sys.argv and max(new/old,newtext/oldtext)>1.05:raise SystemExit('skip timing: body growth still exceeds 5%')
