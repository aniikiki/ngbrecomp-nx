"""Share one mapped-span proof across simple arguments and their guest return PC."""
import re,runpy,sys
from pathlib import Path
p=Path(__file__).parent
arg=r'(?:e(?:ax|cx|dx|bx|bp|si|di)|0x[\dA-Fa-f]+u?|\d+)'
pattern=re.compile(r'(?m)^(?:    PUSH32\(esp, '+arg+r'\);\n)+    PUSH32\(esp, 0x[\dA-Fa-f]+u\); (?=RECOMP_ABI_CALL\()')
def block(raw):
 vals=re.findall(r'PUSH32\(esp, ('+arg+r')\)',raw)
 n=len(vals);assert n>=2
 if n>16:return raw
 # Aligned low/high never cross a page or wrap. No side effects in arguments.
 fast=''.join(f'q[{n-i-1}]={v};' for i,v in enumerate(vals))
 return f'    {{uint32_t low=esp-{4*n}u; unsigned off=low&4095u; if(!(low&3u) && off+{4*n}u<=ngb_fast_page_bytes[low>>12]){{volatile uint32_t *q=(volatile uint32_t*)(ngb_fast_ram+(low&0x7fffffffu));{fast}esp=low;}}else{{\n'+raw+'} } '
def transform(s,u):
 return pattern.sub(lambda m:block(m[0]),s)
units=[2,16,0,28,29]
if __name__=='__main__' and '--check' in sys.argv:
 import subprocess,tempfile
 pairs={}
 for u in units:
  f=Path(f'build/switch-runtime/gen/recomp_{u:04}.c');s=f.read_text()
  for m in pattern.finditer(s):
   if block(m[0])!=m[0]:pairs[m[0]]=block(m[0])
  print('unit',u,len(list(pattern.finditer(s))),'sites')
 # Run original and transformed groups, including the return PC write, on the same VM model.
 src=(p/'stack-groups-check.inc').read_text().replace('side=-32;side<=32','side=-129;side<=129').replace('8192+side*4','8192+side')
 # Pointer mock logs unaligned word faults only for unmapped/cross-page loads; use memcpy via packed words.
 src=src.replace('#define MEM32(a) (*(volatile uint32_t*)ptr(a))','typedef struct __attribute__((packed)){uint32_t v;} unaligned;\n#define MEM32(a) (((volatile unaligned*)ptr(a))->v)')
 for key,i in [('reference',0),('candidate',1)]:
  src+=f'static void {key}(unsigned n){{switch(n){{\n'+''.join(f'case {j}:{{{v[i]}break;}}\n' for j,v in enumerate(pairs.items()))+'default:abort();}}\n'
 src+=f'int main(void){{return check({len(pairs)});}}'
 with tempfile.TemporaryDirectory() as tmp:
  f=Path(tmp)/'check.c';f.write_text(src);exe=f.with_suffix('')
  subprocess.run(['cc','-std=c11','-O0','-fno-strict-aliasing',f,'-o',exe],check=True);subprocess.run([exe],check=True)
elif __name__=='__main__':
 runpy.run_path(str(p/'model-copy.py'))['build']('call-stack',[(True,[2,16]),(False,[0,28,29])],transform)
