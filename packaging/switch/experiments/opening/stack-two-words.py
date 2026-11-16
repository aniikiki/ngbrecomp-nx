"""One x27 four-byte-end check for two adjacent register pushes or pops."""
from pathlib import Path
import re,runpy
units={1:['00039810'],9:['0013CFE0','0013D330','00132250'],15:['001BBFA0','001BBE70']}
reg='(eax|ecx|edx|ebx|ebp|esi|edi)'
pat=re.compile(r'^    (?P<op>PUSH|POP)32\(esp, '+reg+r'\);\n    (?P=op)32\(esp, '+reg+r'\);$',re.M)
def replace(m):
 push=m[1]=='PUSH';r,t=m[2],m[3]
 ops=('q->hi='+r+'; q->lo='+t+'; esp=a;' if push else r+'=q->lo; '+t+'=q->hi; esp=a+8u;')
 return '''    { uint32_t a='''+('esp-8u' if push else 'esp')+''';
      if (__builtin_expect((uint64_t)a+4u < reg_ends[a>>12],1)) {
       struct __attribute__((packed,may_alias)) Pair {uint32_t lo,hi;};
       volatile struct Pair *q=(volatile struct Pair*)(ngb_fast_ram+(a&0x7fffffffu));
       '''+ops+'''
      } else {
'''+m[0]+'''
      }
    }'''
def transform(s,u):
 count=0
 for va in units[u]:
  a=s.index('void sub_'+va+'(void)\n{');z=s.index('\n}',a)
  b,n=pat.subn(replace,s[a:z]);count+=n;s=s[:a]+b+s[z:]
 assert count;print(u,'adjacent register pairs',count,flush=True)
 return s
if __name__=='__main__':
 for base in (0,0x1180000,0x80000000,0xfffff000):
  for offset in range(4096):
   a=base+offset
   for mapped in (False,True):
    assert (a+4<(base+4093 if mapped else 0))==(mapped and offset<=4088)
 runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('stack-two-words',[(False,list(units))],transform)
