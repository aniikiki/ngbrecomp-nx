"""Count actual private-ABI function entrances per opening frame, with no sampling clock."""
from pathlib import Path
import re,sys,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
v=sorted({int(x,16) for x in re.findall(r'^\.global (?:sub_|d3d_orig_)([0-9A-F]+)',(REGS/'entry.S').read_text(),re.M)})
assert 0<min(v)<=max(v)<1<<22 and len(v)<65535
driver='''
static const uint32_t mix_va[]={0,'''+','.join(map(str,v))+'''};
uint16_t mix_id[1<<22];uint32_t mix_n[sizeof(mix_va)/4];unsigned mix_on;
void mix_flip(unsigned f){
 if(!f){for(unsigned i=1;i<sizeof(mix_va)/4;i++)mix_id[mix_va[i]]=i;}
 else{
 fprintf(stderr,"[ENTRY_MIX] %u",f);
 for(unsigned i=0;i<sizeof(mix_va)/4;i++)if(mix_n[i])fprintf(stderr," %x:%u",mix_va[i],mix_n[i]);
 fprintf(stderr,"\\n");
 }
 memset(mix_n,0,sizeof mix_n);mix_on=f<120;
}
'''
s=(RUNTIME.parent/'arm-registers/checkpoint.S').read_text()
k='\tadrp\tx2, ngb_reg_entries';assert s.count(k)==1
s=s.replace(k,''' adrp x1,mix_on
 ldr w1,[x1,:lo12:mix_on]
 cbz w1,.Lmix_done
 lsr w1,w0,#22
 cbnz w1,.Lmix_done
 adrp x1,mix_id
 add x1,x1,:lo12:mix_id
 ldrh w1,[x1,w0,uxtw #1]
 adrp x2,mix_n
 add x2,x2,:lo12:mix_n
 ldr w3,[x2,w1,uxtw #2]
 add w3,w3,#1
 str w3,[x2,w1,uxtw #2]
.Lmix_done:
'''+k)
f=p.out/'mix.S';f.write_text(s);o=f.with_suffix('.o')
subprocess.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(REGS/'checkpoint.o'))]=str(o)
p.driver(driver);s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void mix_flip(unsigned);mix_flip({arg});')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
