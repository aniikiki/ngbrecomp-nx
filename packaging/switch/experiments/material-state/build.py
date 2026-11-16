"""Generate guarded replacements for runs of unchanged original render state.
After a mismatch, run the original setter, then re-read the material. No
guest reference is held over a hook, guest poll, callback or allocation."""
from pathlib import Path
import re,subprocess as sp,sys
p=Path('/work/build/switch-runtime');d=p/'opt050/material';d.mkdir(exist_ok=True)
n='recomp_0028.c';s=(p/'gen'/n).read_text()
rows=[
 ('30B870','30B87B',0x28,0x9777bc,'edi'),
 ('30B893','30B89C',None,0x9777c4,'eax'),
 ('30B8BC','30B8C7',0x30,0x97791c,'eax'),
 ('30B8D2','30B8DD',0x34,0x9778f4,'eax'),
 ('30B8E8','30B8F3',0x38,0x9777c8,'edi'),
 ('30B90B','30B916',0x3c,0x9777cc,'edi'),
 ('30B92E','30B939',0x40,0x977910,'eax'),
 ('30B944','30B94F',0x44,0x9777ec,'edi'),
 ('30B967','30B96F',None,0x97790c,None),
 ('30B97B','30B986',0x2c,0x9777d0,'edi')]
out=[]
for i,(label,bad,off,cache,reg) in enumerate(rows):
 tag='loc_00'+label+': ;'
 start=s.index(tag);end=s.index('loc_00'+bad+': ;',start)
 body=s[start:end];assert ('0x%X'%cache) in body and 'ngb_guest_block_poll' not in body and 'RECOMP_ABI_CALL' not in body,body
 if off:assert ('MEM32(esi + 0x%X)'%off) in body
 # After any original setter, use a fresh check on re-entry. Each original
 # compare is still executed with the same live integer operands.
 s=s.replace(tag,tag+'\n    if (!(esi&3) && (esi >= 0x8000u && esi < NGB_VM_BEGIN-0x48u)) {mp=(const volatile uint32_t*)(ngb_fast_ram+esi);goto material_'+str(i)+';}')
 val=f'mp[{off//4}]' if off else ('ebx' if not reg else 'MEM32(0x9777C4)')
 if reg:out.append(f'material_{i}: {reg}={val};')
 else:out.append(f'material_{i}: ;')
 rhs='0' if i==1 else f'MEM32(0x{cache:X})'
 out.append(f'    if ({reg or val}!={rhs}) goto loc_00{bad};')
out.append('    goto loc_0030B99E;')
k='void sub_0030B7E0(void)\n{';s=s.replace(k,k+'\n    const volatile uint32_t *mp;')
a=s.index('\n}',s.index(k));s=s[:a]+'\n'+'\n'.join(out)+'\n'+s[a:];(d/'fast.c').write_text(s)
abi=Path('/work/packaging/switch/arm-registers')
v=(abi/'compile.py').read_text().replace("o=w.parent/'native-regs'","o=w.parent/'opt050/material'")
v=v.replace(" sp.run(c,cwd=w,check=True)"," c[-1]=str(o/'fast.c')\n sp.run(c,cwd=w,check=True)",1)
v=v[:v.index('with cf.ThreadPoolExecutor')]+"""build('recomp_0028.c')"""
exec(compile(v,'material-private','exec'),{'__name__':'__main__'})
v=(abi/'gates.py').read_text().replace('/switch-runtime/native-regs','/switch-runtime/opt050/material')
exec(compile(v,'material-gates','exec'),{'__name__':'__main__'})
