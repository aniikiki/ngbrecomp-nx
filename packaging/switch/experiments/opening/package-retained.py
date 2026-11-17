"""Cross-link the combined measured candidate locally; never deploy."""
from pathlib import Path
import runpy,sys
p=Path(__file__).resolve().parent
r=runpy.run_path(str(p/'follow-results.py'))['outcome']('retained-default')
assert r['valid_runs']==8 and not r.get('errors'),r
assert len(r['pairs'])==4 and all(x[0]>0 and x[2]>0 and .96<x[1]<1.04 and .96<x[3]<1.04 for x in r['pairs']),r
s=(p/'submit-bound-device.py').read_text()
def replace(k,v):
 global s
 assert s.count(k)==1,k
 s=s.replace(k,v)
replace("out=base/'history'/version;","version='0.55.6-retained';out=base/'history'/version;")
replace(" regs=sorted(reg.glob('recomp_*.c.o'));assert len(regs)==14",""" alt=base/'core-perf/opening-full-page'
 for name in ('vm.c','contiguous.c'):comp(name,(alt/name).read_text())
 renderer=Path('/work/src/d3d/gpu/threaded.cpp').read_text()
 for transform in ('batch-bytes','command-record'):
  renderer=runpy.run_path(str(p/(transform+'.py')))['transform'](renderer)
 comp('threaded.cpp',renderer)
 regs=sorted(alt.glob('recomp_*.c.o'));assert len(regs)==47""")
replace("str(reg/(k+'.o'))","str((alt if k in ('entry','gates') else reg)/(k+'.o'))")
replace("assert b' bd_ticks\\n' in nm","assert all(k in nm for k in (b' bd_ticks\\n',b' opening_end4\\n',b' ngb_reg_xbe_entry_point\\n'))")
hardware_test='--hardware-test' in sys.argv
if hardware_test: sys.argv.extend(['--split-link-audit','--pixel-link-audit'])
if '--split-link-audit' in sys.argv:
 # Use the same transformations as the measured host replay, but compile HLE
 # and hooks with their original Horizon commands. Keep the Draw-bound probe.
 replace("version='0.55.6-retained';out=base/'history'/version;","version='0.55.6-split-audit';out=base/'core-perf/opening-split-link-audit';")
 replace(" s=(Path('/work/src/d3d/hle.cpp')).read_text()", """ class Capture:
  core=d
  link=[str(d/'exact-hooks.c.o')]
  patched={}
  def add(self,name,src):self.patched[name]=src
  def compile(self,name,src,flags):self.patched[name]=src;return name
 cap=Capture()
 runpy.run_path(str(p/'after-regs.py'))['install'](cap,root)
 assert set(cap.patched)=={'hle.cpp','direct/hooks.c'}
 comp('direct/hooks.c',cap.patched['direct/hooks.c'],['-include',str(root/'switch_guest_regs.h')])
 s=cap.patched['hle.cpp']""")
 replace("regs=sorted(alt.glob('recomp_*.c.o'));assert len(regs)==47","""regs=[]
 for u in range(47):
  variant='opening-partition-pgo' if u in (2,10,16,28,29) else 'opening-compact-loops' if u in (26,39) else 'opening-paired-copy' if u==44 else 'opening-full-page'
  obj=alt.parent/variant/f'recomp_{u:04}.c.o';assert obj.exists(),obj
  regs.append(obj)
 assert len(regs)==47""")
 k=" (out/'symbols.gz').write_bytes"
 assert s.count(k)==1
 package_suffix=s[s.index(k):]
 s=s[:s.index(k)]+""" assert b' ngb_after_empty\\n' in nm
 assert b' __gcov_init\\n' not in nm
 Path(out/'linked-inputs.txt').write_text(''.join(hashlib.sha256(o.read_bytes()).hexdigest()+' '+str(o.relative_to(base))+'\\n' for o in regs))
 print('Verified Horizon link, 47 guest objects; temporary ELF removed on exit.',flush=True)
"""
 if '--pixel-link-audit' in sys.argv:
  replace("out=base/'core-perf/opening-split-link-audit'", "out=base/'core-perf/opening-pixel-link-audit'")
  replace("s=cap.patched['hle.cpp']", "s=runpy.run_path(str(p/'pixel-write-plan.py'))['transform'](cap.patched['hle.cpp'])")
  replace(" assert b' ngb_after_empty", " assert b'PlannedPixel' in nm and b'NGB_PIXEL_PLAN_CONTROL' in elf.read_bytes()\n assert b' ngb_after_empty")
 if hardware_test:
  replace("version='0.55.6-split-audit';out=base/'core-perf/opening-pixel-link-audit';","version='0.55.7-open120';out=base/'history'/version;")
  replace(" print('Verified Horizon link, 47 guest objects; temporary ELF removed on exit.',flush=True)", " assert (out/'linked-inputs.txt').read_bytes()==(base/'core-perf/opening-pixel-link-audit/linked-inputs.txt').read_bytes()")
  s+=package_suffix
elif '--pixel-link-audit' in sys.argv:
 raise SystemExit('--pixel-link-audit requires --split-link-audit')
if '--pipe-attribution' in sys.argv:
 assert hardware_test
 replace("version='0.55.7-open120';out=", "version='0.55.7-pipe2';out=")
 replace(" comp('threaded.cpp',renderer)", r""" renderer='extern "C" void pt_wait(bool);\n'+renderer
 for a in ('true','false'):
  k='ngb_direct_render_event(false, '+a+');'
  assert renderer.count(k)==1
  renderer=renderer.replace(k,(k+'pt_wait(true);') if a=='true' else ('pt_wait(false);'+k))
 renderer+='\n'+(p/'pipe-attribution.inc').read_text()+(p/'pipe-attribution-device.inc').read_text()
 comp('threaded.cpp',renderer,['-I/work/xboxrecomp/third_party/volk'])
 link.insert(1,'-Wl,--wrap=volkLoadDeviceTable')""")
 replace(" comp('scene/bridge.c',s)", """ s=once(s,'static void bd_boundary(unsigned f){','extern void pt_flip(unsigned);static void bd_boundary(unsigned f){pt_flip(f);')
 comp('scene/bridge.c',s)""")
 replace(" (out/'symbols.gz').write_bytes"," assert b' __wrap_volkLoadDeviceTable\\n' in nm and b' pt_flip\\n' in nm\n (out/'symbols.gz').write_bytes")
if '--opening-warm' in sys.argv:
 assert '--pipe-attribution' in sys.argv
 # Increment the patch number for the next Switch package built on this baseline.
 warm_version='0.56.0'
 replace("version='0.55.7-pipe2';out=", f"version='{warm_version}';out=")
 replace(" comp('hle.cpp',s)", """ warm=runpy.run_path(str(p/'hardware-prewarm.py'))
 comp('hle.cpp',warm['hle'](s))
 comp('vk/backend.cpp',warm['backend'](Path('/work/src/d3d/vk/backend.cpp').read_text()),['-DNGB_RIGID_CLIP'])""")
 replace("'checkpoint','backend-clip'", "'checkpoint'")
 replace("  if name=='main.c':s+=", """  if name=='runtime.c':
   s=once(s,'        ngb_menu_gpu_prepare();','        ngb_menu_gpu_prepare(); extern void ngb_prepare_title_device(void); uint64_t start=ngb_elapsed_ns(); ngb_prepare_title_device(); char msg[96]; snprintf(msg,sizeof(msg),"3D scene [WARM_TITLE] elapsed_ms=%llu",(unsigned long long)((ngb_elapsed_ns()-start)/1000000)); ngb_kernel_log(msg);')
  if name=='main.c':s+=""")
 replace("  shutil.copyfile(base/'romfs/.ngb-spirv',romfs/'.ngb-spirv')","""  seeds=base/'core-perf/opening-present-combined'
  for a,bname in [('opening-complete.spirv','.ngb-spirv'),('opening-120.recipes','.ngb-recipes')]:
   shutil.copyfile(seeds/a,romfs/bname)""")
 replace("[x.name for x in romfs.iterdir()]==['.ngb-spirv']", "sorted(x.name for x in romfs.iterdir())==['.ngb-recipes','.ngb-spirv']")
 replace("   assert (romfs/'.ngb-spirv').stat().st_size<=size<(romfs/'.ngb-spirv').stat().st_size+65536", """   f.seek(asset+offset);payload=f.read(size)
   assert all(x.read_bytes() in payload for x in romfs.iterdir())""")
if '--texture-preload' in sys.argv:
 assert '--opening-warm' in sys.argv
 replace("version='0.56.0';out=","version='0.56.2';out=")
 replace(" def comp(name,s,flags=[]):",""" runpy.run_path('/work/packaging/switch/texture-preload/index.py')['emit'](Path('/work/game_files'),d/'texture_index.inc')
 def comp(name,s,flags=[]):
  if name in ('files.c','scanout.c','hle.cpp','vk/backend.cpp','threaded.cpp'):
   flags=[*flags,'-DNGB_TEXTURE_PRELOAD','-I'+str(d)]""")
if '--player' in sys.argv:
 assert '--texture-preload' in sys.argv
 replace("version='0.56.2';out=", "version='0.56.24';out=")
 replace(" elf=d/'idx.elf';", " runpy.run_path('/work/packaging/switch/settings/link.py')['install'](commands,b,d,link,regs)\n elf=d/'idx.elf';")
 replace(" (out/'symbols.gz').write_bytes", """ table={v.split()[-1]:v.split() for v in nm.decode().splitlines() if v.split()}
 assert all("ngbs_sub_"+a in table for a in ("001764F0","00176840","00176E30","00177330","001EAA10"))
 assert 'ngb_mission_original' in table and 'ngbs_sub_00175A00' in table and 'ngb_mission_dump' in table
 handlers=[n for n in table if n.startswith('ngbs_sub_')]
 assert "ngbs_sub_002FD3E0" in handlers and len(handlers)>12 and all(table['ngb_reg_'+n[5:]][1:3]==['0000000000000040' if n=='ngbs_sub_00175A00' else '0000000000000030','T'] for n in handlers)
 (out/'symbols.gz').write_bytes""")
 replace(" def comp(name,s,flags=[]):",""" def comp(name,s,flags=[]):
  if name=='opening_movie.c':
   flags=[*flags,'-DNGB_PROLOGUE_START=ngb_reg_sub_003443D0','-DNGB_PROLOGUE_CAPTION=ngb_reg_sub_00344AD0']
   link.insert(1,'-Wl,--wrap=ngb_reg_sub_003443D0,--wrap=ngb_reg_sub_00344AD0')
  flags=[*flags,'-DNGB_PLAYER_BUILD','-include',str(root/'player_diagnostics.h')]""")
 replace(" comp('threaded.cpp',renderer", " comp('menu_gpu.c',(root/'menu_gpu.c').read_text())\n comp('audio_boot.c',(root/'audio_boot.c').read_text())\n comp('shaders.cpp',Path('/work/src/d3d/gpu/shaders.cpp').read_text())\n comp('files_bridge.c',(root/'files_bridge.c').read_text())\n comp('direct/platform.cpp',(root/'direct/platform.cpp').read_text())\n comp('threaded.cpp',renderer")
 # These probes are on the guest-side direct HLE entry points, not the Vulkan worker.
 replace(" comp('hle.cpp',warm['hle'](s))", """ s=once(s,'bool measure = ngb_direct_detail_frame','MP_ADD(MP_VK_DRAW,0,0); bool measure = ngb_direct_detail_frame')
 comp('hle.cpp',warm['hle'](s))""")
 replace("bd_present_mark(); g_backend->Present", "MP_ADD(MP_VK_PRESENT,0,0); if(NGB_DIAG) bd_present_mark(); g_backend->Present")
 replace("pt_flip(f);", "if(!NGB_DIAG)return;pt_flip(f);")
 replace("sdk/'libnx/default_icon.jpg'", "base/'branding/ngb-icon.jpg'")
 replace("'NGB Startup',", "'Ninja Gaiden Black',")
 replace("  seeds=base/", "  shutil.copyfile(base/'branding/loading.rgba',romfs/'loading.rgba')\n  seeds=base/")
 replace("==['.ngb-recipes','.ngb-spirv']", "==['.ngb-recipes','.ngb-spirv','loading.rgba']")
 replace(" assert digest(nro,1)", " assert digest(nro,0)==hashlib.sha256((base/'branding/ngb-icon.jpg').read_bytes()).digest()\n assert digest(nro,1)")
sys.argv=['submit-bound-device.py','--wide','--pad','--movie','--save','--cg','--hold']
exec(compile(s,'submit-bound-device.py','exec'),{'runpy':runpy,'p':p})
