"""Count redundant page-end loads on straight-line fallthrough with a live copy.
Conservative: discard proof on any label, call, unconditional transfer or
unknown instruction. Ordinary guest RAM stores cannot write host page metadata.
This is opportunity accounting in the pre-gate compiler output, not elapsed time.
"""
from pathlib import Path
from collections import Counter
import re
def audit(path):
 gpr=r'[wx](?:[12]?\d|30)'; rows=Counter();vals={};pages={};serial=0;epoch=0;fn='';weight=0
 def clear():
  nonlocal serial,epoch
  serial+=1;epoch=serial;vals.clear();pages.clear()
 def val(reg):
  return vals.get(reg[1:],(epoch,reg[1:]))
 for line in path.open():
  l=line.strip()
  if m:=re.match(r'// BLOCK \d+, count:(\d+)(.*?) seq:',l):
   weight=int(m[1]) if m[2].strip() in ('','(precise)') else 0
   continue
  if l.endswith(':'):
   clear()
   if re.fullmatch(r'\w+:',l):fn=l[:-1];weight=0
   continue
  if l.startswith('.size'):fn='';weight=0
  if not fn or not re.match('^[a-z]',l):continue
  op,_,args=l.partition('\t')
  if not args:op,_,args=l.partition(' ')
  args=args.split('//')[0].strip()
  if op=='ldr' and (m:=re.fullmatch(r'(w\d+), \[x27, (x\d+), lsl 2\]',args)):
   dst,idx=m.groups();key=val(idx);rows['indexed loads']+=weight
   if key in pages and val(pages[key][0])==pages[key][1]:
    rows['live earlier table result']+=weight
    rows['same destination' if pages[key][0]==dst else 'different destination']+=weight
   serial+=1;vals[dst[1:]]=('load',serial);pages[key]=(dst,val(dst))
   continue
  if op in ('cmp','cmn','tst','ccmp','cbz','cbnz','tbz','tbnz') or op.startswith('b.'):continue
  if op.startswith('st') and '!' not in args and '],' not in args:continue
  if op in ('add','sub','and','orr','eor','lsl','lsr','mov','movk','ubfx','adrp','ldr','ldrb','ldrh','csel','mul','madd','sxtw','uxtw') and '!' not in args and '],' not in args:
   parts=args.split(', ');dst=parts[0]
   if re.fullmatch(gpr,dst):
    serial+=1
    if op=='lsr' and len(parts)==3 and parts[0].startswith('w') and re.fullmatch(r'w\d+',parts[1]) and parts[2] in ('12','#12'):
     vals[dst[1:]]=('page32',val(parts[1]))
    else:vals[dst[1:]]=('changed',serial)
   continue
  clear()
 return rows

if __name__=='__main__':
 p=Path(__file__).resolve().parent
 # Same compiler invocation and finalized counters as retained-call-work,
 # but with the exact partitioned variant used in the cumulative replays.
 s=(p/'retained-call-work.py').read_text()
 s=s.replace("'-fno-reorder-blocks-and-partition'","'-freorder-blocks-and-partition'")
 a=s.index('   fn=None;');b=s.index('  finally:',a)
 s=s[:a]+"   r=audit(out);print(u,r,flush=True);assert r['indexed loads']>0\n"+s[b:s.index("print('unit caller")]
 exec(compile(s,'split-page-work','exec'),{'audit':audit})
