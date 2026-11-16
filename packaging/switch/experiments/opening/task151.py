"""Time direct call sites in task 151150 on first-demo flips. Instrumented CPU time, not device ms."""
from pathlib import Path
import re,sys,subprocess,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
geo_cost='--geometry-cost' in sys.argv
select_data='--selection' in sys.argv
geometry=select_data or '--geometry' in sys.argv
children=geo_cost or geometry or '--query-children' in sys.argv
query=children or '--query' in sys.argv
arguments='--arguments' in sys.argv
p=NativeProbe('opening-task151-selection' if select_data else 'opening-task151-geo-cost' if geo_cost else 'opening-task151-geometry' if geometry else 'opening-task151-children' if children else 'opening-task151-query' if query else 'opening-task151-arguments' if arguments else 'opening-task151')
s=(REGS/'recomp_0010.c.gated.s').read_text();wr=''
objects='--objects' in sys.argv or arguments
def event(i):
 save=['sub sp,sp,#688','stp x18,x30,[sp,#144]','mrs x18,nzcv','str x18,[sp,#160]']
 load=['ldr x18,[sp,#160]','msr nzcv,x18','ldp x18,x30,[sp,#144]','add sp,sp,#688']
 for j in range(0,18,2):
  save.append(f'stp x{j},x{j+1},[sp,#{8*j}]');load.insert(0,f'ldp x{j},x{j+1},[sp,#{8*j}]')
 for j in range(0,32,2):
  save.append(f'stp q{j},q{j+1},[sp,#{176+16*j}]');load.insert(0,f'ldp q{j},q{j+1},[sp,#{176+16*j}]')
 extra=['mov w1,w19','mov w2,w22','bl task_object'] if objects and i<128 else []
 return '\n'.join(save+([f'mov w0,#{i}']+extra if extra else [])+[f'mov w0,#{i}','bl task_event']+load)
sites=[]
for parent in ['00151150','00147DF0','00149620']:
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
oi=[i for i,v in enumerate(sites,1) if v.endswith('reg_sub_00148120')]
if query:
 # Track only calls made through either measured parent. Carry the active path in tk,
 # which already follows worker/fiber switches. The clock excludes input comparisons.
 t='ngb_reg_sub_00034E70';a=s.index('ngb_reg_sub_00148120:\n');b=s.index('\t.size\tngb_reg_sub_00148120',a)
 body,n=re.subn(r'(\bbl\s+)'+t+r'\b',r'\1.Lquery_call',s[a:b]);assert n==1;s=s[:a]+body+s[b:]
 def qe(exit):
  return event(0).replace('mov w0,#0\nbl task_event',f'mov w0,#{exit}\nmov w1,w19\nbl query_event')
 wr+='.Lquery_call:\n'+qe(0)+'\nstp x29,x30,[sp,#-16]!\nbl '+t+'\nldp x29,x30,[sp],#16\n'+qe(1)+'\nret\n'
audit=(r"""
static unsigned oa[256],ob[256],na,nb,both,n1,n2,over;
void task_object(unsigned k,unsigned a){if(!tf||owner[k]!=tk)return;unsigned *v,*n;if(k==FIRST){v=oa;n=&na;}else if(k==SECOND){v=ob;n=&nb;}else return;if(*n>=256)abort();v[(*n)++]=a;}
static void audit_frame(unsigned f){if(f>30){n1+=na;n2+=nb;for(unsigned j=0;j<nb;j++)for(unsigned i=0;i<na;i++)if(oa[i]==ob[j]){both++;break;}}na=nb=0;if(f==120)fprintf(stderr,"[OBJECTS] first=%u second=%u repeated_in_other_pass=%u\n",n1,n2,both);}
""".replace('FIRST',str(oi[0])).replace('SECOND',str(oi[1])).replace(',over;', ';')) if objects else 'static void audit_frame(unsigned f){(void)f;}'
if arguments:
 audit=r'''
struct obj_arg{unsigned actor,arg,flags;};
static struct obj_arg oa[256];static unsigned na,n1,n2,actor,match_arg,flag_matches,same;
void task_object(unsigned k,unsigned a,unsigned sp){
 if(!tf||owner[k]!=tk||(k!=FIRST && k!=SECOND))return;
 unsigned v;memcpy(&v,(void*)ngb_guest_pointer(sp+4,4),4);
 const unsigned offs[]={0x278e,0x279f,0x27a0,0x27f0};
 unsigned b=0;for(unsigned j=0;j<4;j++)b|=(unsigned)*(uint8_t*)ngb_guest_pointer(a+offs[j],1)<<(8*j);
 if(k==FIRST){if(na==256)abort();oa[na++]=(struct obj_arg){a,v,b};n1++;return;}
 n2++;unsigned m=0;for(unsigned i=0;i<na;i++)if(oa[i].actor==a){m|=1;if(oa[i].arg==v)m|=2;if(oa[i].flags==b)m|=4;if(oa[i].arg==v&&oa[i].flags==b)m|=8;}
 actor+=!!(m&1);match_arg+=!!(m&2);flag_matches+=!!(m&4);same+=!!(m&8);
}
static void audit_frame(unsigned f){if(f==30||f==120)fprintf(stderr,"[TASK_INPUTS] end=%u first=%u second=%u prior_actor=%u same_arg=%u same_flags=%u both=%u\n",f,n1,n2,actor,match_arg,flag_matches,same);
 if(f==0||f==30){n1=n2=actor=match_arg=flag_matches=same=0;}na=0;}
'''.replace('FIRST',str(oi[0])).replace('SECOND',str(oi[1]))
if query:
 audit=r'''
struct shot { unsigned actor; unsigned char xyz[12],fields[8];unsigned mode;};
static struct shot items[128];static unsigned ni,qcount[2],over,xyz,flags,both;
void query_event(unsigned exiting,unsigned a){
 if(exiting){if(tk==61||tk==62)task_switch(tk==61?FIRST:SECOND);return;}
 if(tk!=FIRST&&tk!=SECOND)return;
 unsigned route=tk==SECOND;
 if(tf){struct shot x={.actor=a};memcpy(x.xyz,(void*)ngb_guest_pointer(a+0x8c0,12),12);
 const unsigned offs[]={0x278e,0x27f0,0x2799,0x279c,0x2774,0x2775,0x279f,0x27a0};
 for(unsigned i=0;i<8;i++)x.fields[i]=*(unsigned char*)ngb_guest_pointer(a+offs[i],1);
 memcpy(&x.mode,(void*)ngb_guest_pointer(0xd21e4c,4),4);qcount[route]++;
 if(!route){if(ni==128)abort();items[ni++]=x;}
 else{unsigned m=0;for(unsigned i=0;i<ni;i++){struct shot *o=items+i;if(o->actor!=a)continue;
 unsigned p=!memcmp(o->xyz,x.xyz,12),q=o->mode==x.mode&&!memcmp(o->fields,x.fields,8);m|=1|(p<<1)|(q<<2)|((p&&q)<<3);}
 over+=m&1;xyz+=(m>>1)&1;flags+=(m>>2)&1;both+=(m>>3)&1;}}
 task_switch(61+route);
}
static void audit_frame(unsigned f){if(f==30||f==120)fprintf(stderr,"[QUERY] end=%u first=%u second=%u same_actor=%u xyz=%u fields=%u both=%u ns=%llu:%llu\n",f,qcount[0],qcount[1],over,xyz,flags,both,(unsigned long long)tsum[61],(unsigned long long)tsum[62]);if(!f||f==30){qcount[0]=qcount[1]=over=xyz=flags=both=0;}ni=0;}
'''.replace('FIRST',str(oi[0])).replace('SECOND',str(oi[1]))
if children:
 # Each direct child gets two lanes. Its return restores the correct traversal.
 qsrc=(REGS/'recomp_0001.c.gated.s').read_text();qw=''
 a=qsrc.index('ngb_reg_sub_00034E70:\n');b=qsrc.index('\t.size\tngb_reg_sub_00034E70',a);body=qsrc[a:b]
 tags=sorted(set(re.findall(r'\bbl\s+(ngb_(?:reg|gate)_sub_[0-9A-F]+)',body)));assert len(tags)<=15
 for i,t in enumerate(tags):
  label=f'.Lquery_child_{i}';body,n=re.subn(r'(\bbl\s+)'+t+r'\b',r'\1'+label,body);assert n==1
  def qc(k):return event(0).replace('mov w0,#0\nbl task_event',f'mov w0,#{k}\nbl query_child')
  qw+=label+':\n'+qc(i)+f'\nstp x29,x30,[sp,#-16]!\nbl {t}\nldp x29,x30,[sp],#16\n'+qc(128+i)+'\nret\n'
 qsrc=qsrc[:a]+body+qsrc[b:]+'\n.text\n'+qw
 audit+=r'''
void query_child(unsigned i){if(i<128){if(tk==61||tk==62){unsigned lane=30+2*i+tk-61;task_switch(lane);if(tf)tc[lane]++;}}
 else if(tk==30+2*(i-128)||tk==31+2*(i-128))task_switch(61+((tk-30)&1));}
'''
 audit=audit.replace('if(f==30||f==120)fprintf','if(f==30||f==120){for(unsigned j=30;j<60;j++)if(tc[j])fprintf(stderr,"[QCHILD] %u %u %u %llu\\n",f,j,tc[j],(unsigned long long)tsum[j]);}if(f==30||f==120)fprintf')
 (p.out/'children.txt').write_text('\n'.join(f'{30+2*i}/{31+2*i} {t}' for i,t in enumerate(tags))+'\n')
if geometry:
 lane=30+2*tags.index('ngb_reg_sub_000355B0')
 inc=Path(__file__).with_name('part-geometry.inc').read_text().replace('GEO_A',str(lane)).replace('GEO_B',str(lane+1))
 audit=inc+audit.replace('static void audit_frame(unsigned f){','static void audit_frame(unsigned f){geo_frame(f);')
 def geo(k):return event(0).replace('mov w0,#0\nbl task_event',f'mov w0,#{k}\nmov w1,w24\nmov w2,w22\nbl geo_event')
 for par,tar,left,right in [('00035940','00035A00',0,3),('00035A00','00305D60',1,2)]+([('00035A00','00035B90',4,5)] if select_data else []):
  a=qsrc.index('ngb_reg_sub_'+par+':\n');b=qsrc.index('\t.size\tngb_reg_sub_'+par,a);body=qsrc[a:b];anchor='bl\tngb_reg_sub_'+tar;assert body.count(anchor)==1
  qsrc=qsrc[:a]+body.replace(anchor,geo(left)+'\n'+anchor+'\n'+geo(right))+qsrc[b:]
if geo_cost:
 lane=30+2*tags.index('ngb_reg_sub_000355B0')
 edges=[('000355B0','00035940',lane),('00035940','00035A00',64),('00035A00','00035B90',66),('00035A00','00305D60',66),('00035A00','0003C7F0',66),('00035A00','00035C70',66)]
 for i,(parent,target,_) in enumerate(edges):
  def ev(k):return event(0).replace('mov w0,#0\nbl task_event',f'mov w0,#{k}\nbl geo_cost_event')
  a=qsrc.index('ngb_reg_sub_'+parent+':\n');b=qsrc.index('\t.size\tngb_reg_sub_'+parent,a);body=qsrc[a:b];k='bl\tngb_reg_sub_'+target;assert body.count(k)==1
  qsrc=qsrc[:a]+body.replace(k,ev(i)+'\n'+k+'\n'+ev(128+i))+qsrc[b:]
 audit+='static const unsigned geo_parent[]={'+','.join(str(t[2]) for t in edges)+'};\n'+r'''
void geo_cost_event(unsigned k){unsigned edge=k&127,p=geo_parent[edge],child=64+2*edge;
 if(k<128 && (tk==p||tk==p+1)){unsigned lane=child+tk-p;task_switch(lane);if(tf)tc[lane]++;}
 else if(k>=128&&(tk==child||tk==child+1))task_switch(p+tk-child);}
'''
 audit=audit.replace('for(unsigned j=30;j<60;j++)','for(unsigned j=30;j<76;j++)')
p.driver('static const unsigned owner[]={'+','.join(map(str,owner))+'};\n'+r'''
static unsigned tf,tk,tc[96];static uint64_t tn,tsum[96];
static uint64_t task_ns(void){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return t.tv_sec*1000000000ull+t.tv_nsec;}
unsigned task_switch(unsigned k){unsigned old=tk;uint64_t now=task_ns();if(tf && tk)tsum[tk]+=now-tn;tn=now;tk=k;return old;}
void task_event(unsigned k){if(k<128){if(owner[k]!=tk)return;task_switch(k);if(tf)tc[k]++;}else if(tk==k-128)task_switch(owner[tk]);}
'''+audit+r'''
void task_flip(unsigned f){audit_frame(f);task_switch(tk);if(f==0||f==30){memset(tc,0,sizeof tc);memset(tsum,0,sizeof tsum);}if(f==120)for(unsigned i=1;i<64;i++)if(tc[i]||tsum[i])fprintf(stderr,"[TASK151] %u %u %llu\n",i,tc[i],(unsigned long long)tsum[i]);tf=f<120;}
''')
s+='\n.text\n'+wr
v=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert v.count(k)==1;v=v.replace(k,k+f' extern void task_flip(unsigned);task_flip({f});')
p.add('scene/bridge.c',v)
with tempfile.TemporaryDirectory(dir=p.out) as tmp:
 if children:
  q=Path(tmp)/'child.s';q.write_text(qsrc);o=q.with_suffix('.o');subprocess.run(['cc','-c',q,'-o',o],check=True);p.link[p.link.index(str(REGS/'recomp_0001.c.o'))]=str(o)
 f=Path(tmp)/'task.s';o=f.with_suffix('.o');f.write_text(s);subprocess.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(REGS/'recomp_0010.c.o'))]=str(o);p.link.insert(1,'-Wl,--strip-debug');p.finish()
(p.out/'task151-sites.txt').write_text('\n'.join(f'{i} {t}' for i,t in enumerate(sites,1))+'\n')
