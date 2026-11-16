"""Pass the six Before inputs directly across the C/C++ boundary; preserve original
snapshot and stack-pop semantics if an XDK call is taken. Host A/B only."""
from pathlib import Path
import re
names=('EAX','ECX','EDX','EBX','ESP','ESI')
params=', '.join('uint32_t in_'+x for x in names)
args=', '.join('in_'+x for x in names)
decl='uint32_t ngb_before_scalar(int fn, '+params+')'
def hle(s):
 a=s.index('bool Before(int fn, Call c) {');b=s.index('// after the recompiled body',a)
 body=s[a:b];assert set(re.findall(r'c\.r\[(\w+)\]',body))==set(names)
 assert re.findall(r'return (\w+);',body)==['false','false']
 body=body.replace('bool Before(int fn, Call c) {','bool Before(int fn, '+params+') {\n    const auto stack_arg=[in_ESP](int i){return R32(in_ESP+4+4*i);};\n    const auto stack_float=[&](int i){uint32_t w=stack_arg(i);float v;std::memcpy(&v,&w,4);return v;};')
 for x in names:body=body.replace('c.r['+x+']','in_'+x)
 body=body.replace('c.a(','stack_arg(').replace('c.af(','stack_float(');assert not re.search(r'\bc\.',body)
 s=s[:a]+body+s[b:]
 a=s.index('extern "C" int d3d_hle_call(');b=s.index('\n}',a)+2
 init=s[s.index('{',a)+1:s.index('    bool took = Before',a)]
 assert '4 + g_take_ret[fn]' in s[a:b]
 new='extern "C" '+decl+' {'+init+'    Before(fn, '+args+');\n    return g_backend && unsigned(fn)<D3DF_COUNT && g_take[fn] ? 4u+g_take_ret[fn] : 0u;\n}\n'
 new+='extern "C" int d3d_hle_call(int fn,uint32_t regs[8]){uint32_t step=ngb_before_scalar(fn,'+','.join('regs['+x+']' for x in names)+');if(!step)return 0;regs[EAX]=0;regs[ESP]+=step;return 1;}'
 return s[:a]+new+s[b:]
def hooks(s):
 s=s.replace('int d3d_hle_call(int fn, uint32_t regs[8]);',decl+';')
 k='int took = d3d_hle_call(fn, regs);';assert s.count(k)==1
 s=s.replace(k,'uint32_t took = ngb_before_scalar(fn,regs[0],regs[1],regs[2],regs[3],regs[4],regs[6]);')
 a=s.index('int d3d_hook(int fn)');b=s.index('void d3d_after',a)
 block=s[a:b];assert block.count('eax = regs[0]')==block.count('esp = regs[4]')==1
 return s[:a]+block.replace('eax = regs[0]','eax = 0').replace('esp = regs[4]','esp = regs[4]+took')+s[b:]
def install(p,r):
 for n,func in [('hle.cpp',hle),('direct/hooks.c',hooks)]:
  f=p.out/Path(n).name
  assert p.link.count(str(f)+'.o')==1
  p.compile(n,func(f.read_text()),['-include',str(r/'switch_guest_regs.h')] if n.endswith('.c') else [])
