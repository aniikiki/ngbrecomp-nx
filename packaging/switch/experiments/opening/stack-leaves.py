"""Use one page validation after entry for a straight-line guest leaf. Rewrite
only proven SP-relative memory operations in that interval. No service call,
back edge, memory-map mutation or guest stack pivot is allowed in a leaf."""
from pathlib import Path
import os,re,sys,collections
root=Path('/work') if Path('/work/packaging').is_dir() else Path.cwd()
base=root/'build/switch-runtime';abi=root/'packaging/switch/arm-registers'
scan='--scan' in sys.argv
d=base/'core-perf/opening-stack-leaves'; units=(0,1,2,3,9,10,11,14,16,27,28,29,37,44)
log=(base/'core-perf/opening-setup/entry-mix.log').read_text()
counts=collections.Counter()
for f,ls in re.findall(r'^\[ENTRY_MIX\] (\d+) (.*)$',log,re.M):
 if 31<=int(f)<=120:
  for va,n in re.findall(r'([0-9a-f]+):(\d+)',ls):counts[int(va,16)]+=int(n)
types={'MEM32':'uint32_t','MEM16':'uint16_t','MEM8':'uint8_t','MEMF':'float','MEMD':'double','SMEM32':'int32_t','SMEM16':'int16_t','SMEM8':'int8_t'}
width={'MEMD':8,'MEMF':4,**{a:int(a.split('MEM')[1])//8 for a in types if a[-1].isdigit()}}
ops=re.compile(r'\b('+'|'.join(types)+r')\(esp(?: ([+-]) (0x[0-9A-Fa-f]+|\d+))?\)')
stats=[]
def transform(m):
 name,va,entry,body=m[1],int(m[2],16),m[3],m[4]
 if counts[va]<90:return m[0]
 clean=re.sub(r'/\*.*?\*/','',body,flags=re.S)
 if re.search(r'\b(?:goto|if|switch|for|while|RECOMP_\w+|sub_[0-9A-F]+|d3d_\w+|ngb_\w+|arm_\w+)\s*\b|^\s*#',clean,re.M):return m[0]
 if clean.count('return;')!=1 or not clean.strip().endswith('return;'):return m[0]
 # An allowed helper may access guest RAM or stop on a fault, but cannot invoke
 # a callback or change the mapping, nor modify ESP. Reject all other calls.
 calls=set(re.findall(r'\b([A-Za-z_]\w*)\s*\(',clean))
 if calls-set(types)-{'PUSH32','POP32','XMM_MEM','XMM_STORE','XMM_SCALAR','XMM_ADD','XMM_MUL','XMM_SUB','XMM_SHUFFLE','XMM_AND','XMM_OR','XMM_XOR','void','sizeof'}:return m[0]
 if len(re.findall(r'^loc_\w+:',body,re.M))!=1:return m[0]
 delta=0; touched=[];res=[]
 for l in body.splitlines(True):
  plain=l.split('/*')[0].strip()
  mp=re.fullmatch(r'PUSH32\(esp, (\w+)\);',plain)
  mo=re.fullmatch(r'POP32\(esp, (eax|ebx|ecx|edx|esi|edi|ebp)\);',plain)
  adj=re.match(r'esp ([+-])= (0x[0-9A-Fa-f]+|\d+);',plain)
  if mp:
   if mp[1]=='esp':return m[0]
   delta-=4;touched.append((delta,4));l=f'    esp -= 4; *(volatile uint32_t *)(stack_base+({delta}))={mp[1]};\n'
  elif mo:
   touched.append((delta,4));l=f'    {mo[1]}=*(volatile uint32_t *)(stack_base+({delta})); esp+=4;\n';delta+=4
  elif adj:delta+=int(adj[2],0)*(1 if adj[1]=='+' else -1)
  else:
   def rewrite(v):
    off=delta+(int(v[3],0)*(-1 if v[2]=='-' else 1) if v[3] else 0)
    touched.append((off,width[v[1]]));return f'(*(volatile {types[v[1]]} *)(stack_base+({off})))'
   l=ops.sub(rewrite,l)
   if re.search(r'\besp\b',l.split('/*')[0]):return m[0]
  res.append(l)
 if len(touched)<3:return m[0]
 lo=min(k for k,w in touched);hi=max(k+w for k,w in touched)
 if hi-lo>512:return m[0]
 # Checked interval fits one page; compute host bias from the validated low VA.
 pos='uint32_t stack_lo=esp+('+str(lo)+');'
 guard=f'(stack_lo&4095u)+{hi-lo}u<=ngb_fast_page_bytes[stack_lo>>12]'
 fast=''.join(res);fast=re.sub(r'^loc_\w+: ;','',fast,flags=re.M)
 stats.append((counts[va],len(touched),va))
 return entry+'\n    '+pos+f' if({guard}){{uintptr_t stack_base=(uintptr_t)ngb_fast_ram+(stack_lo&0x7fffffffu)-({lo});\n'+fast+'    }\n'+body+'}'
if not scan:d.mkdir(exist_ok=True)
for u in units:
 name=f'recomp_{u:04}.c';s=(base/'gen'/name).read_text()
 # 1=symbol, 2=VA, 3=entry declaration and checkpoint, 4=remaining body.
 pat=r'(?=void ((?:sub_|d3d_orig_)([0-9A-F]+))\(void\))(^void \w+\(void\)\n\{\n    RECOMP_ENTRY\(0x[0-9A-F]+u\);)(.*?^)\}'
 s=re.sub(pat,transform,s,flags=re.S|re.M)
 if not scan:(d/name).write_text(s)
print('straight-line leaf count',len(stats),'observed entries/frame',sum(n for n,_,_ in stats)/90,'stack operations/frame',sum(n*k for n,k,_ in stats)/90,flush=True)
if scan:sys.exit()
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text();k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k,' c[-1]=str(o/n)\n'+k)
exec(compile(s,'leaf-abi','exec'),{})
exec(compile((abi/'gates.py').read_text(),'leaf-gates','exec'),{})
for pat in ('recomp_*.s','recomp_*.c'):
 for f in d.glob(pat):f.unlink()
