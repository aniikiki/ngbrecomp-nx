"""Fuse a straight-line SSE run only if every guest address is ordinary RAM.
No callbacks, control transfers, or changing address registers inside a run.
A failed range test runs the complete original instructions in order."""
import re,collections
reg=r'(?:eax|ebx|ecx|edx|esi|edi|esp|ebp)'
addr=r'(?:'+reg+r'(?: \+ (?:0x[\dA-Fa-f]+|\d+))?|0x[\dA-Fa-f]+)'
mem=re.compile(r'\b(XMM_MEM|MEMF|MEM32|XMM_STORE)\(('+addr+r')([,)])')
line=re.compile(r'^    (?:xmm[0-7](?:\.[fu]\[\d\])?\s*(?:[+*/-]?=)|XMM_STORE\().+;')
allowed={'XMM_ZERO','XMM_SCALAR','XMM_SCALAR_BITS','XMM_SHUFFLE','XMM_ADD','XMM_SUB','XMM_MUL','XMM_AND','XMM_OR','XMM_XOR','XMM_MEM','XMM_STORE','MEMF','MEM32'}
def fuse(src):
 count=0;buf=[];out=[]
 def flush():
  nonlocal count
  run=''.join(buf);buf.clear()
  hits=list(mem.finditer(run)); xs=sorted(set(re.findall(r'\bxmm[0-7]\b',run)))
  if len(hits)<2 or len(xs)<1 or len(run.splitlines())<5:return run
  spans={};refs={}
  for m in hits:
   v=m[2].split(' + ');base=v[0];off=int(v[1],0) if len(v)>1 else 0
   if base.startswith('0x'):off=int(base,16);base='0'
   width=16 if m[1].startswith('XMM') else 4
   lo,hi=spans.get(base,(off,off));spans[base]=(min(lo,off),max(hi,off+width));refs[m[2]]=(base,off)
  if len(spans)>5 or any(hi-lo>4096 for lo,hi in spans.values()):return run
  if len(hits)<=len(spans):return run
  count+=1
  prefix='{\n';checks=[]
  for b,(lo,hi) in spans.items():
   prefix+=f' uint32_t va_{b}=({b})+{lo}u;\n'
   checks.append(f'(va_{b}&4095u)+{hi-lo}u<=ngb_fast_page_bytes[va_{b}>>12]')
  prefix+=' if(__builtin_expect('+ ' && '.join(checks)+',1)){\n'
  for b in spans:prefix+=f' unsigned char *ptr_{b}=ngb_fast_ram+(va_{b}&0x7fffffffu);\n'
  prefix+=' RecompXmm '+','.join(f'v_{x}={x}' for x in xs)+';\n'
  def sub(m):
   op,orig,end=m.groups();b,off=refs[orig];ptr=f'(ptr_{b}+{off-spans[b][0]})'
   if op=='XMM_MEM':return 'NG_LOAD('+ptr+')'
   if op=='XMM_STORE':return 'NG_STORE('+ptr+','
   return '(*(volatile '+('float' if op=='MEMF' else 'uint32_t')+'*)'+ptr+')'
  fast=mem.sub(sub,run);fast=re.sub(r'\bxmm[0-7]\b',lambda m:'v_'+m[0],fast)
  return prefix+fast+''.join(f' {x}=v_{x};\n' for x in xs)+' }else{\n'+run+' }\n}\n'
 for l in src.splitlines(True):
  code=l.split('/*')[0];calls=set(re.findall(r'\b(\w+)\(',code))
  if line.match(code) and calls<=allowed and len(mem.findall(code))==len(re.findall(r'\b(?:XMM_MEM|MEMF|MEM32|XMM_STORE)\(',code)) and not re.search(r'[{}]|\+\+|--',code):buf.append(l)
  else:out.extend([flush(),l])
 out.append(flush());return ''.join(out),count
