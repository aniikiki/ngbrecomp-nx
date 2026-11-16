from pathlib import Path
import gzip,bisect,re,sys
def sy(p):
 f=gzip.open(p,'rt') if p.suffix=='.gz' else p.open()
 with f:return {a[3]:(int(a[0],16),int(a[1],16)) for l in f if len(a:=l.split())==4 and a[2] in ('T','t') and re.fullmatch(r'(?:(?:ngb_reg_|ngb_gate_)?(?:sub_|d3d_orig_)[0-9A-F]+|ngb_gate_\w+|ngb_reg_checkpoint|xbe_entry_point)',a[3])}
d=Path('build/switch-runtime/opt050');bt=d/'bolt';h=sy(d/'codetrace/host-symbols.txt');target=sy(Path(sys.argv[1]))
f=sorted((a,k,n) for n,(a,k) in h.items() if n in target and target[n][1]==k and k);a=[v[0] for v in f]
def resolve(pc):
 i=bisect.bisect_right(a,pc)-1
 if i>=0 and pc<a[i]+f[i][1]:return f[i][2],pc-a[i]
total=0;names=set()
with (bt/'profile.fdata').open('w') as out:
 for l in (bt/'edges').open():
  x,y,k=l.split();x=resolve(int(x,16));y=resolve(int(y,16))
  if not x or not y:continue
  print(f'1 {x[0]} {x[1]:x} 1 {y[0]} {y[1]:x} 0 {k}',file=out);total+=int(k);names.update((x[0],y[0]))
(bt/'names').write_text('\n'.join(sorted(names))+'\n');print('profiled functions',len(names),'transfers',total)
