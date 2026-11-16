"""Count actual effective guest scalar addresses in four opening-hot units.
This instrumented build is for access distributions, never timing. Use the
47-unit private symbol set and replace just the four measured objects."""
from pathlib import Path
import re,os
root=Path('/work');base=root/'build/switch-runtime';abi=root/'packaging/switch/arm-registers'
d=base/'core-perf/opening-memory-census';d.mkdir(exist_ok=True)
units=(2,16,26,39)
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text()
s=re.sub(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))',s,flags=re.M)
num=r'(?:sub_|d3d_orig_)[0-9A-F]+'
s=s.replace(num,'(?:'+num+'|xbe_entry_point)')
s=s[:s.index("f=o/'entry.S'")];s=s.replace('ex.map(build,units)','ex.map(build,'+repr([f'recomp_{i:04}.c' for i in units])+')')
mem=(abi.parent/'runtime/guest_memory.h').read_text()
k='    if (ngb_static_image_span(address, bytes) && ngb_fast_ram)'
assert mem.count(k)==1
mem=mem.replace(k,'''    extern unsigned census_active;
    extern uint64_t census_rows[4][7];
    if(census_active){
      unsigned c;
      if(__builtin_constant_p(address))c=0;
      else if((uint32_t)(address-0x8000u)<=0x01000000u-0x8000u-bytes)c=1;
      else if((uint32_t)(address-g_esp+4096u)<8192u)c=2;
      else if(address>=0x01000000 && address<NGB_VM_END)c=3;
      else if(address<0x04000000)c=4;
      else if((address&0x80000000u) && address<0x88000000u)c=5;
      else c=6;
      census_rows[CENSUS_UNIT][c]++;
    }
'''+k)
(d/'template.h').write_text(mem)
s=s.replace("(r/'guest_memory.h').read_text()","(o/'template.h').read_text()")
k=' sp.run(c,cwd=w,check=True)';assert s.count(k)==1
s=s.replace(k,' c.insert(-1,"-DCENSUS_UNIT="+str('+repr(units)+'.index(int(n[7:11]))))\n'+k)
exec(compile(s,'memory-census','exec'),{})
exec(compile((abi/'gates.py').read_text(),'memory-census-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
