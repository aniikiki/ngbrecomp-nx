"""Exclusive host thread time in the part loop, its direct children and mesh grandchildren."""
from pathlib import Path
import re,sys,subprocess,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-part-budget')
s=(REGS/'recomp_0028.c.gated.s').read_text();wr=''
def event(i):
 save=['sub sp,sp,#688','stp x18,x30,[sp,#144]','mrs x18,nzcv','str x18,[sp,#160]']
 load=['ldr x18,[sp,#160]','msr nzcv,x18','ldp x18,x30,[sp,#144]','add sp,sp,#688']
 for j in range(0,18,2):
  save.append(f'stp x{j},x{j+1},[sp,#{8*j}]');load.insert(0,f'ldp x{j},x{j+1},[sp,#{8*j}]')
 for j in range(0,32,2):
  save.append(f'stp q{j},q{j+1},[sp,#{176+16*j}]');load.insert(0,f'ldp q{j},q{j+1},[sp,#{176+16*j}]')
 return '\n'.join(save+[f'mov w0,#{i}','bl task_event']+load)
sites=['root ngb_reg_sub_003078B0']
k='ngb_reg_sub_003078B0:\n';assert s.count(k)==1
s=s.replace(k,k+event(1)+'\nstp x29,x30,[sp,#-16]!\nbl .Lpart_body\nldp x29,x30,[sp],#16\n'+event(129)+'\nret\n.Lpart_body:\n')
for parent in ['003078B0','0030BCA0']:
 a=s.index('ngb_reg_sub_'+parent+':\n');b=s.index('\t.size\tngb_reg_sub_'+parent,a);body=s[a:b]
 for t in sorted(set(re.findall(r'\bbl\s+(ngb_(?:reg|gate)_sub_[0-9A-F]+)',body))):
  sites.append(parent+' '+t);i=len(sites)
  body,n=re.subn(r'(\bbl\s+)'+t+r'\b',lambda m:m[1]+f'.Ltask_{i}',body);assert n
  wr+=f'.Ltask_{i}:\n'+event(i)+f'\nstp x29,x30,[sp,#-16]!\nbl {t}\nldp x29,x30,[sp],#16\n'+event(128+i)+'\nret\n'
 s=s[:a]+body+s[b:]
assert len(sites)<64
owner=[0]+[next((j for j,v in enumerate(sites,1) if v.endswith('sub_'+row.split()[0])),0) for row in sites]
workers=(RUNTIME/'workers.inc').read_text()
for typ in ('worker','fiber'):
 key='static struct '+typ+' {';assert workers.count(key)==1;workers=workers.replace(key,key+'\n unsigned tscope;')
for dest in ('dest','next'):
 key=f'ngb_ctx_switch(&old->sp, {dest}->sp);';assert workers.count(key)==1
 workers=workers.replace(key,f'old->tscope=task_switch({dest}->tscope); '+key)
(p.out/'workers.inc').write_text('unsigned task_switch(unsigned);\n'+workers)
(p.out/'host-runtime.inc').write_text((REGS/'host-runtime.inc').read_text())
p.driver('static const unsigned owner[]={'+','.join(map(str,owner))+'};\n'+r'''
static unsigned tf,tk,tc[64];static uint64_t tn,tsum[64];
static uint64_t task_ns(void){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return t.tv_sec*1000000000ull+t.tv_nsec;}
unsigned task_switch(unsigned k){unsigned old=tk;uint64_t now=task_ns();if(tf && tk)tsum[tk]+=now-tn;tn=now;tk=k;return old;}
void task_event(unsigned k){if(k<128){if(owner[k]!=tk)return;task_switch(k);if(tf)tc[k]++;}else if(tk==k-128)task_switch(owner[tk]);}

void task_flip(unsigned f){task_switch(tk);if(f==30||f==120)for(unsigned i=1;i<64;i++)if(tc[i]||tsum[i])fprintf(stderr,"[PART_BUDGET] %u %u %u %llu\n",f,i,tc[i],(unsigned long long)tsum[i]);if(!f||f==30){memset(tc,0,sizeof tc);memset(tsum,0,sizeof tsum);}tf=f<120;}
''')
s+='\n.text\n'+wr
v=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert v.count(k)==1;v=v.replace(k,k+f' extern void task_flip(unsigned);task_flip({f});')
p.add('scene/bridge.c',v)
with tempfile.TemporaryDirectory(dir=p.out) as tmp:
 f=Path(tmp)/'task.s';o=f.with_suffix('.o');f.write_text(s);subprocess.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(REGS/'recomp_0028.c.o'))]=str(o);p.link.insert(1,'-Wl,--strip-debug');p.finish()
(p.out/'part-sites.txt').write_text('\n'.join(f'{i} {t}' for i,t in enumerate(sites,1))+'\n')
