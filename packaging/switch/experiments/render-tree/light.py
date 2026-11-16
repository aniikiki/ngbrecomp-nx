from pathlib import Path
import shlex,subprocess as sp,sys,json
h=Path(__file__).resolve().parent;w=Path('/work');p=w/'build/switch-runtime';d=p/'core-perf/render-light';d.mkdir(exist_ok=True);perf=h.parents[1]/'perf'
if sys.argv[1]=='cross':
 n='recomp_0044.c';s=(p/'gen'/n).read_text()
 a=s.index('loc_003C7850:');i=s.index('    esi = MEM32(0x3D83C8);',a)
 assert 'PUSH32(esp, esi);' in s[a:i] and 'PUSH32(esp, edi);' not in s[a:i]
 s='extern unsigned light_trial_active,light_trial_hits;\n'+s[:i]+(h/'light.inc').read_text()+s[i:]
 f=d/n;f.write_text(s)
 c=next(shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=p/'switch',text=True).splitlines() if x.endswith('/'+n))
 o=str(f)+'.o';c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(f);c.insert(-1,'-g0');sp.run(c,cwd=p/'switch',check=True)
else:
 sys.path.insert(0,str(perf));from native_probe import NativeProbe,RUNTIME
 q=NativeProbe('render-light');q.link=json.loads((q.core/'exact-link.json').read_text())
 q.link[q.link.index(next(v for v in q.link if v.endswith('/recomp_0044.o')))]=str(d/'recomp_0044.c.o')
 driver=(q.core/'exact-test.c').read_text();tag='void __real_ngb_kernel_log'
 driver=driver.replace(tag,(perf/'trial.inc').read_text()+'unsigned light_trial_active,light_trial_hits;\n'+tag)
 q.link[q.link.index(str(q.core/'exact-runtime_test.c.o'))]=q.compile('runtime_test.c',driver,['-include',str(RUNTIME/'switch_guest_regs.h'),'-I'+str(q.core),'-I'+str(RUNTIME)])
 s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;'
 q.add('scene/bridge.c',s.replace(k,k+' extern unsigned trial_variant,light_trial_active,light_trial_hits;extern void ngb_trial_flip(unsigned,unsigned); if(!(scene_flips%120))fprintf(stderr,"[LIGHT] %u %u\\n",scene_flips,light_trial_hits);ngb_trial_flip(scene_flips,draws);light_trial_active=trial_variant;'));q.finish()
