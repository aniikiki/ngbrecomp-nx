from pathlib import Path
import runpy,tempfile,subprocess
d=Path(__file__).resolve().parent
impl=runpy.run_path(str(d/'stack-two-words.py'));pat=impl['pat']
s=(d/'stack-groups-check.inc').read_text().replace('static uintptr_t ptr','static uint32_t reg_ends[4];\nstatic uintptr_t ptr').replace('side*4','side').replace('initial.r[4]=','for(int j=0;j<4;j++)reg_ends[j]=ngb_fast_page_bytes[j]>=4?j*4096u+ngb_fast_page_bytes[j]-3u:0;\n   initial.r[4]=')
s=s.replace('#define MEM32(a) (*(volatile uint32_t*)ptr(a))','struct __attribute__((packed,may_alias)) Word{uint32_t value;};\n#define MEM32(a) (((volatile struct Word*)ptr(a))->value)')
regs='eax ecx edx ebx ebp esi edi'.split()
ss=[f'    {op}32(esp, {r});\n    {op}32(esp, {t});' for op in ('PUSH','POP') for r in regs for t in regs]
for name in ('reference','candidate'):
 s+='\nstatic void '+name+'(unsigned i){switch(i){'
 for i,case in enumerate(ss):
  v=pat.sub(impl['replace'],case) if name=='candidate' else case
  assert name=='reference' or v!=case
  s+=f'case {i}: {{\n'+v+'\n}break;\n'
 s+='}}'
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'t.c').write_text(s+'\nint main(void){return check(98);}')
 subprocess.run(['cc','-O2',p/'t.c','-o',p/'check'],check=True);subprocess.run([p/'check'],check=True)
