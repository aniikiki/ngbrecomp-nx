"""Run the real Direct3D active-scene decision and early special-method switch for every added method."""
from pathlib import Path
import runpy,re,tempfile,subprocess
d=Path(__file__).parent
s=Path('packaging/switch/runtime/nv2a_boot.c').read_text();b=Path('packaging/switch/runtime/scene/bridge.c').read_text()
def extract(s,key):
 a=s.index(key);return s[a:s.index('\n}',a)+2]
cls='static unsigned state_packet_size'
orig=extract(s,cls);new=extract(runpy.run_path(str(d/'dma-state-families.py'))['transform'](s),cls)
s1=b.index('    switch (method)',b.index('int ngb_scene_method('));s2=b.index('    if (!device)',s1)
# Any early case (including a flip) is ineligible for this optimization.
early=b[s1:s2];early=early[:early.index('        if (device)')]+early[early.index('        return 0;'):]
a=b.index('    if (ngb_scene_active) {',b.index('#ifdef NGB_DIRECT3D',b.index('return 0;',b.index('} else if (method == NV097_INLINE_ARRAY'))))
active=b[a:b.index('\n#endif',a)]
code='#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include "nv2a_regs.h"\n'+extract(s,'static unsigned direct_state_words')+'\n'+orig.replace('state_packet_size','before')+'\n'+new.replace('state_packet_size','after')+'''
static unsigned draws,ngb_scene_active=1,regs[0x2000/4];
static int consumed(unsigned method,unsigned value){
'''+early+active+'''
return 0;}
int main(void){unsigned new_cases=0;for(unsigned m=0;m<=0x1ffc;m+=4)for(unsigned n=0;n<=2047;n++){
 unsigned h=m|(n<<18),o=before(h),v=after(h);
 if(o && o!=v)abort();
 if(v!=o){
 if(!n||v!=n+1||after(h|0x40000000)||after(h|0x2000))abort();
 for(unsigned j=0;j<n;j++)for(unsigned t=0;t<2;t++){
 if(!consumed(m+4*j,t?0xabcdef:0)||draws||regs[NV_PGRAPH_ZSTENCILCLEARVALUE/4]||regs[NV_PGRAPH_COLORCLEARVALUE/4])abort();}
 ++new_cases;}}
 printf("verified %u newly accepted start/count combinations\\n",new_cases);return !new_cases;}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.c').write_text(code);subprocess.run(['cc','-O2','-Ixboxrecomp/src/nv2a',p/'test.c','-o',p/'t'],check=True);subprocess.run([p/'t'],check=True)
