"""Instrument only the C++ allocation/deallocation ABI actually linked by the ARM host replay."""
from pathlib import Path
ops=[('_Znwm','void *','size_t bytes','bytes','bytes'),('_Znam','void *','size_t bytes','bytes','bytes'),
     ('_ZdlPvm','void','void *ptr,size_t bytes','ptr,bytes','0'),('_ZdaPv','void','void *ptr','ptr','0')]
def instrument():
 s=Path(__file__).with_name('bulk-budget.inc').read_text()
 a=s.index('void *__real_memcpy');b=s.index('struct bulkrow',a)
 s=s[:a]+''.join(f'{ret} __real_{n}({args});\n' for n,ret,args,_,_ in ops)+s[b:]
 a=s.index('#define BULK_WRAP');b=s.index('void phase_flip',a)
 tmpl=s[s.index(' bulk_busy=1;',a):s.index('void *v=__real_',a)].replace(chr(92)+'\n','\n').replace('bulk_rng>>27','bulk_rng>>29')
 wrap=''
 for i,(name,ret,args,call,size) in enumerate(ops):
  stmt=f'__real_{name}({call});'
  early='return '+stmt if ret!='void' else '{'+stmt+'return;}'
  wrap+=f'__attribute__((noinline)) {ret} __wrap_{name}({args}){{\n if(!bulk_on || bulk_busy)'+early+'\n'
  wrap+=tmpl.replace('opid',str(i)).replace('r->bytes+=bytes','r->bytes+='+size)
  wrap+=('void *v=' if ret!='void' else '')+stmt+'\n if(mode==0){r->ns+=bulk_clock()-start;r->n++;}bulk_busy=0;'+('return v;' if ret!='void' else '')+'}\n'
 return (s[:a]+wrap+s[b:]).replace('[BULK]','[ALLOC]').replace('__real_memset','memset')
