"""Guard stack-only arithmetic sections between guest polls. Keep all real loads/stores."""
import re,runpy
from pathlib import Path
def transform(s,u):
 start=s.index('void sub_003433F0(void)\n{');stop=s.index('\n}',start)
 body=s[start:stop]
 matches=[]
 pat=re.compile(r'MEM32\(esp \+ (0x[0-9A-F]+)\)')
 for m in re.finditer(r'^loc_(00343[456][0-9A-F]{2}): ;[^\n]*\n(.*?)(?=^loc_|\Z)',body,re.M|re.S):
  # Restrict to the inner loop. Only clone the uninterrupted stretch from
  # the first to last direct stack reference, not polls or foreign accesses.
  if not 0x3434d0<=int(m[1],16)<=0x343657:continue
  lines=m[2].splitlines(True)
  if m[1]=='00343657':lines=lines[next(i for i,l in enumerate(lines) if 'MEM32(esp + 0x3C) = edx;' in l):]
  if m[1]=='0034357F':lines=lines[:next(i for i,l in enumerate(lines) if 'MEM16(ebp)' in l)]
  idx=[i for i,l in enumerate(lines) if pat.search(l)]
  if len(idx)<3:continue
  a=idx[0];b=idx[-1]+1
  # If an imul is part of the region, include its closing brace.
  while sum(l.count('{')-l.count('}') for l in lines[a:b])>0:b+=1
  if b>len(lines):continue
  raw=''.join(lines[a:b])
  if raw.count('{')!=raw.count('}') or re.search(r'(?:(?:S?MEM\d+)|PUSH32|POP32|goto|poll|CALL|\besp\s*=)',pat.sub('',raw)):continue
  offs=[int(v,16) for v in pat.findall(raw)];lo,hi=min(offs),max(offs)
  fast=pat.sub(lambda x:'(*(volatile uint32_t *)(stp+'+str(int(x[1],16)-lo)+'))',raw)
  merged=f'    {{ uint32_t stlo=esp+{lo}u; if (__builtin_expect((uint64_t)stlo+{hi-lo}u<reg_ends[stlo>>12],1)) {{ unsigned char *stp=ngb_fast_ram+(stlo&0x7fffffffu);\n'+fast+'    }else{\n'+raw+'    }}\n'
  matches.append((raw,merged,m[1],len(offs)))
 assert len(matches)==5 and any(x[2]=='00343657' for x in matches)
 for raw,v,k,n in matches:
  assert body.count(raw)==1;body=body.replace(raw,v);print('stack span',k,n,flush=True)
 return s[:start]+body+s[stop:]
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('stack-inner-span',[(False,[33])],transform)
