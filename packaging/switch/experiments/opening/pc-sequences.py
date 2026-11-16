"""Count interrupted instruction addresses in a verified scalar translation
sequence. Never charge the consuming guest load/store or stack ancestors."""
import re,subprocess,collections,sys
from pathlib import Path
base=Path('build/switch-runtime')
rows=[s.split('\t') for s in (base/'core-perf/opening-setup/leaf-budget.tsv').read_text().splitlines() if '\t' in s]
elf=base/'native-regs/ngb-startup.elf'
tool=subprocess.check_output(['xcrun','-f','llvm-objdump'],text=True).strip()
nro=(base/'history/0.51.0-rc1/ngb-startup.nro').open('rb')
samples=collections.Counter();parts=collections.Counter()
for row in rows:
 if not 31<=int(row[0])<=120:continue
 if not row[3].startswith('ngb_reg_'):continue
 pc=int(row[2],16)
 dis=subprocess.check_output([tool,'-d',f'--start-address={pc-44}',f'--stop-address={pc+48}',elf],text=True)
 ins={}
 for m in re.finditer(r'^\s*([0-9a-f]+): ([0-9a-f]{8})\s+(\S+)\s*([^\n]*)',dis,re.M):
  addr=int(m[1],16);nro.seek(addr);assert nro.read(4)==bytes.fromhex(m[2])[::-1]
  ins[addr]=(m[3],m[4].split('//')[0].strip())
 # Anchor the actual x27 table load. Only charge recognized adjacent operations
 # in one proven span; stop before any unrelated instruction or branch target.
 for addr,(op,arg) in ins.items():
  m=re.fullmatch(r'w(\d+), \[x27, x(\d+), lsl #1\]',arg)
  if not m or op!='ldrh':continue
  span={addr:'table load'};idx=m[2];dst=m[1]
  for j in (1,2,3):
   sub=ins.get(addr-4*j,('',''));q=re.fullmatch(fr'w{idx}, w(\d+), #12',sub[1])
   if sub[0]=='lsr' and q:span[addr-4*j]='page number';break
   if sub[0]!='mov':break
  for j in range(1,8):
   op,arg=ins.get(addr+j*4,('',''))
   cat=None
   if op=='and' and arg.endswith('#0xfff'):cat='page offset'
   elif op=='add' and re.fullmatch(r'w(\d+), w\1, #0x(?:1|2|4|8|10)',arg):cat='end offset'
   elif op=='cmp' and re.fullmatch(fr'w{dst}, w\d+',arg):cat='bounds compare'
   elif op in ('b.lo','b.hs','b.hi','b.ls') and span.get(addr+(j-1)*4)=='bounds compare':cat='bounds branch'
   elif op=='and' and arg.endswith('#0x7fffffff'):cat='alias mask'
   elif op=='add' and ', x26, ' in arg:cat='RAM base'
   if not cat:break
   span[addr+j*4]=cat
  if pc in span:samples[row[4]]+=1;parts[span[pc]]+=1;break
print('31..120 verified private-ABI page sequence hits',sum(parts.values()),'of',sum(31<=int(r[0])<=120 for r in rows),'samples')
print('operations:',dict(parts));print('previous attribution:',dict(samples))
