"""Specialize the opening's shared oriented-box query, preserving guest side effects.
Use exactly the generated arithmetic and spill writes. Fall back for page splits,
special pages, overlapping stack/inputs, and resume original code before the poll."""
from pathlib import Path
import re,subprocess,shlex
b=Path('/work/build/switch-runtime');work=b/'switch';d=b/'core-perf/wide-start'
s=(b/'gen/recomp_0026.c').read_text()
a=s.index('loc_002E4489: ;');z=s.index('loc_002E4586: ;',a);block=s[a:z]
fast=block
# Stack temporaries assigned to eax/ecx by the generated instruction stream.
for old,new,n in [('MEMF(eax)', 'CPOINT(0)',1),('MEMF(eax + 4)','CPOINT(4)',1),('MEMF(eax + 8)','CPOINT(8)',1)]:
 assert old in fast
 fast=fast.replace(old,new,n)
for addr,off in [('eax','0'),('eax + 4','4'),('eax + 8','8')]:
 fast=fast.replace('MEMF('+addr+')','CSTACK(16+'+off+')')
for off in ('',' + 0x10',' + 0x20'):
 fast=fast.replace('XMM_MEM(ecx'+off+')','CROW('+str(0 if not off else int(off[3:],16))+')')
fast=fast.replace('XMM_STORE_LOW(eax, xmm2);','__builtin_memcpy(cs+16,&xmm2,8);')
fast=re.sub(r'MEMF\(edx \+ (0x\w+)\)',r'CBOX(\1)',fast)
fast=re.sub(r'MEMF\(esp \+ (0x\w+|\d+)\)',r'CSTACK(\1)',fast)
fast=re.sub(r'MEM32\(esp \+ (0x\w+|\d+)\)',r'CU32(\1)',fast)
assert 'MEMF(' not in fast.replace('MEMF(0x4148C8)','') and 'MEM32(' not in fast and 'XMM_MEM(' not in fast
fast=re.sub(r'loc_002E(\w+): ;',r'fast_2e\1: ;',fast)
fast=fast[fast.index('    xmm1 ='):]
tag='loc_002E4489: ;'
new=r"""
    if (span_pick && ((esp|eax|edx)&3u)==0 &&
        (esp&4095u)+32<=ngb_fast_page_bytes[esp>>12] &&
        (edx&4095u)+0x9c<=ngb_fast_page_bytes[edx>>12] &&
        (eax&4095u)+12<=ngb_fast_page_bytes[eax>>12]) {
        unsigned char *cs=ngb_fast_ram+(esp&0x7fffffffu), *cp=ngb_fast_ram+(eax&0x7fffffffu),
                      *cb=ngb_fast_ram+(edx&0x7fffffffu);
        if((cs+32<=cp || cp+12<=cs) && (cs+32<=cb || cb+0x9c<=cs)){
#define CPOINT(o) (*(float*)(cp+(o)))
#define CSTACK(o) (*(float*)(cs+(o)))
#define CU32(o) (*(uint32_t*)(cs+(o)))
#define CBOX(o) (*(float*)(cb+(o)))
#define CROW(o) __extension__ ({RecompXmm row;__builtin_memcpy(&row,cb+0x40+(o),16);row;})
"""+fast+r"""
        goto loc_002E4586;
#undef CPOINT
#undef CSTACK
#undef CU32
#undef CBOX
#undef CROW
        }
    }
"""
s='extern unsigned span_pick;\n'+s[:a]+s[a:].replace(tag,tag+new,1)
# Compile only this object, all other units stay byte-for-byte the same.
cmd=next(shlex.split(x) for x in subprocess.check_output(['ninja','-t','commands','ngb-startup'],cwd=work,text=True).splitlines() if x.endswith('/recomp_0026.c'))
f=d/'collision-span.c';f.write_text(s);cmd[-1]=str(f);cmd[1:1]=['-I'+str(b/'gen')];cmd.insert(-1,'-g0');cmd[cmd.index('-o')+1]=str(d/'collision-span.o');cmd[cmd.index('-MF')+1]=str(d/'collision-span.d');subprocess.run(cmd,cwd=work,check=True)
