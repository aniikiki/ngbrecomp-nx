"""Host-only wide demo: sample completed Vulkan scanouts, not the 4:3 title hash."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'perf'))
from native_probe import NativeProbe, REGS, RUNTIME

p = NativeProbe('wide-start')
if '--present-mix' in sys.argv or '--draw-correspondence' in sys.argv or '--word-site-census' in sys.argv or '--stack-window' in sys.argv or '--target-hist' in sys.argv or '--alloc-budget' in sys.argv or '--bulk-budget' in sys.argv or '--gate-pairs' in sys.argv or '--entry-stream' in sys.argv or '--pointer-sites' in sys.argv or '--scalar-slow' in sys.argv or '--lookup-mix' in sys.argv or '--index-origin' in sys.argv or '--header-sets' in sys.argv or '--pipeline-wait' in sys.argv or '--wait-origin' in sys.argv or '--fifo-groups' in sys.argv or '--clock-census' in sys.argv or '--tree-pair-cost' in sys.argv or '--tree-triple' in sys.argv or '--mixed-hit' in sys.argv or '--mixed-span' in sys.argv or '--axis-parent' in sys.argv or '--axis-query' in sys.argv or '--actor-tree' in sys.argv or '--actor-values' in sys.argv or '--actor-table' in sys.argv or '--light-budget' in sys.argv or '--light-path' in sys.argv or '--public-entry' in sys.argv or '--contact-budget' in sys.argv or '--matrix-budget' in sys.argv or '--row-bins' in sys.argv or '--row-reasons' in sys.argv or '--copy-coverage' in sys.argv or '--light-count' in sys.argv or '--audio-budget' in sys.argv or '--node-budget' in sys.argv or '--node-prefix' in sys.argv or '--family-budget' in sys.argv or '--node-family' in sys.argv or '--node-order' in sys.argv or '--node-census' in sys.argv or '--vm-block-census' in sys.argv or '--sync-budget' in sys.argv or '--delta-gap' in sys.argv or '--range-census' in sys.argv or '--snapshot-budget' in sys.argv or '--light-stages' in sys.argv or '--tree-census' in sys.argv or '--gate-census' in sys.argv or '--pointer-route' in sys.argv or '--cmd-budget' in sys.argv or '--cmd-pass' in sys.argv or '--box-budget' in sys.argv or '--box-scan' in sys.argv or '--box-reuse' in sys.argv or '--page-shape' in sys.argv or '--contact-repeat' in sys.argv or '--contact-blocks' in sys.argv or '--frame-pc' in sys.argv or '--poll-sample' in sys.argv or '--first-init' in sys.argv or '--memory-census' in sys.argv or '--span-audit' in sys.argv or '--irq-cost' in sys.argv or '--model-nodes' in sys.argv or '--tree-update' in sys.argv or '--cb-cost' in sys.argv or '--task-cb' in sys.argv or '--task-edges' in sys.argv or {'--actor-phase','--product-reuse','--actor-kinds','--actor-time'} & set(sys.argv):
    # Attribution is not a timing run. Keep its ELF, source and HDD isolated
    # from the shared ABBA symlink and save tree.
    original=p.out;p.out=p.core/('opening-rng-correspondence' if '--rng-correspondence' in sys.argv else 'opening-present-combined' if '--present-combined' in sys.argv else 'opening-present-mix' if '--present-mix' in sys.argv else 'opening-draw-correspondence' if '--draw-correspondence' in sys.argv else 'opening-word-runs' if '--word-runs' in sys.argv else 'opening-table-locality' if '--table-locality' in sys.argv else 'opening-word-eligibility' if '--word-eligibility' in sys.argv else 'opening-word-address-census' if '--word-address-census' in sys.argv else 'opening-word-site-census' if '--word-site-census' in sys.argv else 'opening-low-prefix-sample' if '--low-prefix-sample' in sys.argv else 'opening-stack-window' if '--stack-window' in sys.argv else 'opening-target-hist' if '--target-hist' in sys.argv else 'opening-alloc-budget' if '--alloc-budget' in sys.argv else 'opening-bulk-budget' if '--bulk-budget' in sys.argv else 'opening-gate-pairs' if '--gate-pairs' in sys.argv else 'opening-stack-distance' if '--stack-distance' in sys.argv else 'opening-copy-profile' if '--copy-profile' in sys.argv else 'opening-inverse-inputs' if '--inverse-inputs' in sys.argv else 'opening-guest-sites' if '--guest-sites' in sys.argv else 'opening-entry-stream' if '--entry-stream' in sys.argv else 'opening-pointer-sites' if '--pointer-sites' in sys.argv else 'opening-scalar-slow' if '--scalar-slow' in sys.argv else 'opening-lookup-mix' if '--lookup-mix' in sys.argv else 'opening-index-origin' if '--index-origin' in sys.argv else 'opening-header-sets' if '--header-sets' in sys.argv else 'opening-pipeline-wait' if '--pipeline-wait' in sys.argv else 'opening-wait-origin' if '--wait-origin' in sys.argv else 'opening-fifo-groups' if '--fifo-groups' in sys.argv else 'opening-clock-census' if '--clock-census' in sys.argv else 'opening-mesh-expensive-target' if '--mesh-expensive-target' in sys.argv else 'opening-mesh-expensive-setup' if '--mesh-expensive-setup' in sys.argv else 'opening-mesh-common-setup' if '--mesh-common-setup' in sys.argv else 'opening-mesh-common-cost' if '--mesh-common-cost' in sys.argv else 'opening-mesh-expensive-cost' if '--mesh-expensive-cost' in sys.argv else 'opening-setup-cost' if '--setup-cost' in sys.argv else 'opening-material-op-cost' if '--material-op-cost' in sys.argv else 'opening-material-callback-cost' if '--material-callback-cost' in sys.argv else 'opening-mesh-cost' if '--mesh-cost' in sys.argv else 'opening-mesh-key-paths' if '--mesh-key-paths' in sys.argv else 'opening-mesh-paths' if '--mesh-paths' in sys.argv else 'opening-task200-cost' if '--task200-cost' in sys.argv else 'opening-task2ae-cost' if '--task2ae-cost' in sys.argv else 'opening-task298-cost' if '--task298-cost' in sys.argv else 'opening-script-loop-cost' if '--script-loop-cost' in sys.argv else 'opening-script-arm-cost' if '--script-arm-cost' in sys.argv else 'opening-shader-child' if '--shader-child' in sys.argv else 'opening-tree-draw-cost' if '--tree-draw-cost' in sys.argv else 'opening-tree-pair-cost' if '--tree-pair-cost' in sys.argv else 'opening-tree-triple' if '--tree-triple' in sys.argv else 'opening-mixed-hit' if '--mixed-hit' in sys.argv else 'opening-mixed-span' if '--mixed-span' in sys.argv else 'opening-axis-parent' if '--axis-parent' in sys.argv else 'opening-axis-query' if '--axis-query' in sys.argv else 'opening-actor-tree' if '--actor-tree' in sys.argv else 'opening-actor-values' if '--actor-values' in sys.argv else 'opening-actor-table' if '--actor-table' in sys.argv else 'opening-light-budget' if '--light-budget' in sys.argv else 'opening-light-path' if '--light-path' in sys.argv else 'opening-public-entry' if '--public-entry' in sys.argv else 'opening-contact-budget' if '--contact-budget' in sys.argv else 'opening-matrix-budget' if '--matrix-budget' in sys.argv else 'opening-row-bins' if '--row-bins' in sys.argv else 'opening-row-reasons' if '--row-reasons' in sys.argv else 'opening-copy-coverage' if '--copy-coverage' in sys.argv else 'opening-light-count' if '--light-count' in sys.argv else 'opening-audio-budget' if '--audio-budget' in sys.argv else 'opening-node-budget' if '--node-budget' in sys.argv else 'opening-node-prefix' if '--node-prefix' in sys.argv else 'opening-family-budget' if '--family-budget' in sys.argv else 'opening-node-family' if '--node-family' in sys.argv else 'opening-node-order' if '--node-order' in sys.argv else 'opening-node-census' if '--node-census' in sys.argv else 'opening-vm-block-census' if '--vm-block-census' in sys.argv else 'opening-sync-budget' if '--sync-budget' in sys.argv else 'opening-delta-gap' if '--delta-gap' in sys.argv else 'opening-strip-footprint' if '--strip-footprint' in sys.argv else 'opening-strip-reason' if '--strip-reason' in sys.argv else 'opening-draw-shader-reuse' if '--draw-shader-detail' in sys.argv and '--shader-bank' in sys.argv else 'opening-draw-shader-detail' if '--draw-shader-detail' in sys.argv else 'opening-draw-separation' if '--draw-separation' in sys.argv else 'opening-range-census' if '--range-census' in sys.argv else 'opening-snapshot-budget' if '--snapshot-budget' in sys.argv else 'opening-light-stages' if '--light-stages' in sys.argv else 'opening-tree-census' if '--tree-census' in sys.argv else 'opening-gate-census' if '--gate-census' in sys.argv else 'opening-pointer-route' if '--pointer-route' in sys.argv else 'opening-page-operands' if '--page-operands' in sys.argv else 'opening-compact-profile' if '--compact-profile' in sys.argv else 'opening-after-profile' if '--after-profile' in sys.argv else 'opening-hot-profile' if '--hot-profile' in sys.argv else 'opening-cmd-budget' if '--cmd-budget' in sys.argv else 'opening-cmd-pass' if '--cmd-pass' in sys.argv else 'opening-box-budget' if '--box-budget' in sys.argv else 'opening-box-scan' if '--box-scan' in sys.argv else 'opening-box-reuse' if '--box-reuse' in sys.argv else 'opening-page-shape' if '--page-shape' in sys.argv else 'opening-contact-repeat' if '--contact-repeat' in sys.argv else 'opening-contact-blocks' if '--contact-blocks' in sys.argv else 'opening-frame-pc' if '--frame-pc' in sys.argv else 'opening-poll-sample' if '--poll-sample' in sys.argv else 'opening-first-init' if '--first-init' in sys.argv else 'opening-span-audit' if '--span-audit' in sys.argv else 'opening-irq-cost' if '--irq-cost' in sys.argv else 'opening-model-nodes' if '--model-nodes' in sys.argv else 'opening-tree-update' if '--tree-update' in sys.argv else 'opening-cb-cost' if '--cb-cost' in sys.argv else 'opening-task-cb' if '--task-cb' in sys.argv else 'opening-task-edges' if '--task-edges' in sys.argv else 'opening-actor-time' if '--actor-time' in sys.argv else 'opening-actor-kinds' if '--actor-kinds' in sys.argv else 'opening-product-reuse' if '--product-reuse' in sys.argv else 'opening-actor-phase' if '--actor-phase' in sys.argv else 'opening-memory-census')/'host';p.out.mkdir(exist_ok=True)
    import shutil
    for name in ('identity.c.o','scanout.c.o','files.c.o','opening_movie.c.o','host-runtime.inc'):
        shutil.copyfile(original/name,p.out/name)
src = (REGS / 'host-driver.c').read_text()
anchor = 'void __real_ngb_kernel_log'
assert src.count(anchor) == 1
src = src.replace(anchor, r'''
#include <stdatomic.h>
static atomic_uint moving_scanouts;
void __real_ngb_scanout_direct(const void *);
void __wrap_ngb_scanout_direct(const void *frame) {
    static uint32_t previous[24*20];
    static unsigned seen;
    const uint32_t *pixels = frame;
    unsigned changed = 0, colored = 0;
    for (unsigned i = 0; i < 24*20; ++i) {
        uint32_t rgb = pixels[((i/24)*NGB_SCAN_H/20+8)*NGB_SCAN_W+(i%24)*NGB_SCAN_W/24+8];
        unsigned diff = 0;
        for (unsigned shift = 0; shift < 24; shift += 8)
            diff += abs((int)((rgb >> shift)&255) - (int)((previous[i] >> shift)&255));
        changed += diff > 15;
        colored += (rgb&255) > 48;
        previous[i] = rgb;
    }
    if (seen++ && changed > 25 && colored > 80) atomic_fetch_add(&moving_scanouts, 1);
    __real_ngb_scanout_direct(frame);
}
''' + anchor)
if '--recipe-pixels' in sys.argv:
    assert '--title-pipeline-prep' in sys.argv or '--strip-snapshot-join' in sys.argv or '--strip-join-control' in sys.argv
    k='    const uint32_t *pixels = frame;'
    assert src.count(k)==1
    src=src.replace(k,k+r"""
    static uint32_t lut[256];
    if(!seen)for(unsigned i=0;i<256;i++){uint32_t c=i;for(int j=0;j<8;j++)c=(c>>1)^((0u-(c&1u))&0xedb88320u);lut[i]=c;}
    if(getenv("NGB_OPEN_PIXEL_DIFF") && (seen==14 || (seen>=75 && seen<=78))){
      char name[160];snprintf(name,sizeof(name),"%s/pic-%u",getenv("NGB_OPEN_PIXEL_DIFF"),seen+1);
      int save=getenv("NGB_OPEN_PIXEL_REFERENCE")!=NULL;
      FILE *f=fopen(name,save?"wb":"rb");if(!f)abort();
      if(save){if(fwrite(frame,4,NGB_SCAN_W*NGB_SCAN_H,f)!=NGB_SCAN_W*NGB_SCAN_H)abort();}
      else{
        uint32_t row[NGB_SCAN_W];unsigned diff=0,alpha=0,peak=0;
        for(unsigned y=0;y<NGB_SCAN_H;y++){if(fread(row,4,NGB_SCAN_W,f)!=NGB_SCAN_W)abort();
          for(unsigned x=0;x<NGB_SCAN_W;x++){uint32_t v=pixels[y*NGB_SCAN_W+x],r=row[x],z=v^r;
            diff+=(z&0xffffff)!=0;alpha+=(z>>24)!=0;
            for(unsigned b=0;b<24;b+=8){unsigned e=abs((int)((v>>b)&255)-(int)((r>>b)&255));if(e>peak)peak=e;}
          }}
        fprintf(stderr,"[PIXEL_DIFF] %u rgb=%u alpha=%u peak=%u\n",seen+1,diff,alpha,peak);
      }
      if(fclose(f))abort();
    }
    uint32_t crc=0xffffffffu;
    for(size_t i=0;i<NGB_SCAN_W*NGB_SCAN_H*4;i++)crc=lut[(crc^((const uint8_t*)frame)[i])&255]^(crc>>8);
    fprintf(stderr,"[OPEN_PIXELS] %u %08x\n",seen,~crc);
""")
anchor = '        CHECK(benchmark_motion);\n        ngb_stop("verified 120'
assert src.count(anchor) == 1
src = src.replace(anchor, '''        fprintf(stderr,"[WIDE] moving Vulkan scanouts=%u\\n",atomic_load(&moving_scanouts));
        CHECK(atomic_load(&moving_scanouts) >= 8);
        ngb_stop("verified 120''')
src = src.replace(' && getenv("NGB_TEST_STORY")) {\n        static uint64_t prev_cpu',' && benchmark_scene) {\n        static uint64_t prev_cpu',1)
if '--irq-cost' in sys.argv:
    import runpy
    rt=(p.out/'host-runtime.inc').read_text()
    (p.out/'irq-runtime.inc').write_text(runpy.run_path(str(Path(__file__).with_name('irq-cost.py')))['instrument'](rt))
    assert src.count('"host-runtime.inc"')==1
    src=src.replace('"host-runtime.inc"','"irq-runtime.inc"')
if '--model-nodes' in sys.argv:
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('model-nodes.py')))['install'](p,REGS,src)
if '--tree-update' in sys.argv:
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('tree-update-budget.py')))['install'](p,REGS,RUNTIME,src)
if '--cb-cost' in sys.argv or '--task-cb' in sys.argv or '--task-edges' in sys.argv:
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('callback-ledger.py')))['install'](p,REGS,RUNTIME,src,outer=bool({'--task-cb','--task-edges'}&set(sys.argv)),branches='--task-edges' in sys.argv)
if '--gate-census' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned gate_counts[2],gate_enabled;
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[GATE_CENSUS] %u %u %u\n",f,gate_counts[0],gate_counts[1]);
 if(!f||f==30)memset(gate_counts,0,sizeof gate_counts);
 gate_enabled=f<120;
}
void __real_ngb_kernel_log''',1)
if '--pointer-route' in sys.argv:
    rt=(p.out/'host-runtime.inc').read_text()
    k='uintptr_t ngb_guest_pointer(uint32_t va, size_t bytes)\n{'
    assert rt.count(k)==1
    rt=rt.replace(k,r'''
static _Thread_local unsigned route_active,route_calls[8][5];
void phase_flip(unsigned f){
 if(f==30 || f==120){for(unsigned r=0;r<8;r++)fprintf(stderr,"[PTR_ROUTE] %u %u %u %u %u %u %u\n",f,r,route_calls[r][0],route_calls[r][1],route_calls[r][2],route_calls[r][3],route_calls[r][4]);}
 if(!f||f==30)memset(route_calls,0,sizeof route_calls);
 route_active=f<120;
}
'''+k+r'''
    if(route_active){
        uint32_t phys=va-0x80000000u;
        unsigned r=!bytes?0:va<RAM_BYTES?(va>=NGB_VM_BEGIN && va<NGB_VM_END?2:1):phys<0x08000000u?
            (ngb_scene_active && ngb_contiguous_pages[phys>>12] && !ngb_target_pages[phys>>12] &&
             (bytes==1?8:bytes)<=4096-(phys&4095)?3:4):5;
        unsigned w=bytes==1?0:bytes==4?1:bytes==16?2:bytes<=64?3:4;
        route_calls[r][w]++;
    }''')
    (p.out/'route-runtime.inc').write_text(rt)
    src=src.replace('"host-runtime.inc"','"route-runtime.inc"')
if '--frame-pc' in sys.argv:
    rt=(p.out/'host-runtime.inc').read_text()
    k='    clock_gettime(CLOCK_MONOTONIC, &ts);';assert rt.count(k)==1
    rt=rt.replace(k,'    uintptr_t old=clock_parent;clock_parent=(uintptr_t)__builtin_return_address(0);\n'+k+'\n    clock_parent=old;')
    k='static uint64_t now_ns(void)';assert rt.count(k)==1
    rt=rt.replace(k,'static __attribute__((noinline)) uint64_t now_ns(void)')
    k='uint64_t ngb_elapsed_ns(void) { return now_ns() - start_ns; }';assert rt.count(k)==1
    rt=rt.replace(k,'__attribute__((noinline)) uint64_t ngb_elapsed_ns(void) { uintptr_t old=elapsed_parent;elapsed_parent=(uintptr_t)__builtin_return_address(0);uint64_t t=now_ns()-start_ns;elapsed_parent=old;return t; }')
    (p.out/'origin-runtime.inc').write_text(rt)
    src=src.replace('"host-runtime.inc"','"origin-runtime.inc"')
    probe=Path(__file__).with_name('frame-pc.inc').read_text()
    if '--xdk-pc-scope' in sys.argv:
        import runpy
        probe=runpy.run_path(str(Path(__file__).with_name('xdk-pc-scope.py')))['install'](p,RUNTIME,probe)
        if '--xdk-memory-operand' in sys.argv:
            probe=runpy.run_path(str(Path(__file__).with_name('memory-operand.py')))['install'](probe)

    if '--page-operands' in sys.argv:
        import runpy
        probe=runpy.run_path(str(Path(__file__).with_name('page-operands.py')))['instrument'](probe)
    if '--low-prefix-sample' in sys.argv:
        import runpy
        probe=runpy.run_path(str(Path(__file__).with_name('low-prefix-sample.py')))['instrument'](probe)
    if '--stack-distance' in sys.argv:
        import runpy
        probe=runpy.run_path(str(Path(__file__).with_name('stack-distance.py')))['instrument'](probe)
    src='#define _GNU_SOURCE 1\n'+probe+src
    p.link.insert(1,'-Wl,--wrap=clock_gettime')
    p.link.insert(1,'-no-pie')
if '--poll-sample' in sys.argv:
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('poll-sample.py')))['install'](p,RUNTIME,src)
if '--first-init' in sys.argv:
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('first-init.py')))['install'](p,src)
if {'--actor-phase','--product-reuse','--actor-kinds','--actor-time'} & set(sys.argv):
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('actor-time.py' if '--actor-time' in sys.argv else 'actor-kinds.py' if '--actor-kinds' in sys.argv else 'product-reuse.py' if '--product-reuse' in sys.argv else 'actor-phase.py')))['install'](p,REGS,src)
if '--timer-mask' in sys.argv:
    import runpy
    obj=p.compile('timers.c',runpy.run_path(str(Path(__file__).with_name('timer-mask.py')))['transform']((RUNTIME/'timers.c').read_text()))
    ix=[i for i,v in enumerate(p.link) if v.endswith('/timers.c.o')]
    assert len(ix)==1
    p.link[ix[0]]=obj
    rt=(p.out/'host-runtime.inc').read_text()
    k='ngb_timers_poll(now_ns() / 100, fire_timer);';assert rt.count(k)==1
    (p.out/'timer-mask-runtime.inc').write_text(rt.replace(k,'extern unsigned ngb_armed_slots; if(ngb_armed_slots) '+k))
    src=src.replace('"host-runtime.inc"','"timer-mask-runtime.inc"')
if '--service-cost' in sys.argv:
    import runpy
    api=runpy.run_path(str(Path(__file__).with_name('service-cost.py')))
    service_obj=p.compile('timers.c',api['timers']((RUNTIME/'timers.c').read_text()))
    ix=[i for i,v in enumerate(p.link) if v.endswith('/timers.c.o')]
    assert len(ix)==1
    p.link[ix[0]]=service_obj
    (p.out/'service-workers.inc').write_text(api['workers']((RUNTIME/'workers.inc').read_text()))
    rt=(p.out/'host-runtime.inc').read_text()
    assert rt.count('#include "workers.inc"')==1
    (p.out/'service-runtime.inc').write_text(rt.replace('#include "workers.inc"','#include "service-workers.inc"'))
    assert src.count('"host-runtime.inc"')==1
    src=src.replace('"host-runtime.inc"','"service-runtime.inc"')
if '--scalar-slow' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('scalar-slow.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
    p.link.insert(1,'-Wl,--wrap=ngb_guest_scalar_fallback')
if '--lookup-mix' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('lookup-mix.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
    p.link.insert(1,'-Wl,--wrap=recomp_lookup')
if '--compare' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('compare-budget.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
    bridge=(RUNTIME/'scene/bridge.c').read_text()
    k='    ++scene_flips;'
    assert bridge.count(k)==1
    p.add('scene/bridge.c',bridge.replace(k,k+' extern void cmp_boundary(unsigned);cmp_boundary(scene_flips);'))
    p.link[1:1]=['-no-pie','-Wl,--wrap=memcmp']
if {'--entry-chains','--stream-layout','--pc-density','--hot-layout'} & set(sys.argv):
    import runpy
    ld=p.out/'hot-layout.ld'
    runpy.run_path(str(Path(__file__).with_name('entry-chains.py' if '--entry-chains' in sys.argv else 'stream-layout.py' if '--stream-layout' in sys.argv else 'pc-density.py' if '--pc-density' in sys.argv else 'hot-layout.py')))['script'](REGS.parent,ld)
    p.link.insert(1,'-Wl,-T,'+str(ld))
if '--angles' in sys.argv:
    src = src.replace('void __real_ngb_kernel_log', Path(__file__).with_name('angle-reuse.inc').read_text() + '\nvoid __real_ngb_kernel_log',1)
    anchor = 'CHECK(sscanf(message,"3D scene flips=%u draws=%u",&flip,&draws)==2);'
    assert src.count(anchor) == 1
    src = src.replace(anchor, anchor + 'angle_frame(flip);')
    p.link.insert(1,'-Wl,--wrap=sin,--wrap=cos,--wrap=sincos')
if '--cache' in sys.argv:
    import subprocess
    asm = (REGS/'recomp_0029.c.gated.s').read_text()
    lo = asm.index('ngb_reg_sub_00317DC0:\n')
    hi = asm.index('\n\t.size\tngb_reg_sub_00317DC0,', lo)
    block = asm[lo:hi]
    for op in ('sin','cos'):
        call = '\tbl\t'+op+'\n'
        assert block.count(call)==2
        block = block.replace(call,'\tbl\tmaterial_'+op+'\n')
    f = p.out/'angle-guest.s'
    f.write_text(asm[:lo]+block+asm[hi:])
    obj = str(f.with_suffix('.o'))
    subprocess.run(['cc','-c',f,'-o',obj],check=True)
    p.link[p.link.index(str(REGS/'recomp_0029.c.o'))]=obj
    impl = '#include <math.h>\n'+Path(__file__).with_name('angle-cache.inc').read_text()
    if '--verify' in sys.argv: impl = '#define NGB_ANGLE_VERIFY\n'+impl
    src = src.replace('void __real_ngb_kernel_log',impl+'\nvoid __real_ngb_kernel_log',1)
if set(sys.argv)&{'--live-matrices','--live-matrices-audit'}:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('live-matrices.py')))['install'](p,'--live-matrices-audit' in sys.argv)
if '--detail-cost' in sys.argv:
    t=(RUNTIME/'direct/hooks.c').read_text()
    for a,b in [('full_timing || ((completed & 15u) == ((group * 9u) & 15u))','((void)group, 0)'),('    ngb_direct_detail_frame = 1;','    ngb_direct_detail_frame = 0;')]:
        assert t.count(a)==1
        t=t.replace(a,b)
    p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=p.compile('direct/hooks.c',t,['-include',str(RUNTIME/'switch_guest_regs.h')])
if '--draw-lto' in sys.argv:
    assert {'--after-regs','--command-record'} <= set(sys.argv)
    # Compile only native draw-path units as IR. The guest code, including
    # hand-written register bridges, stays opaque. Preserve existing FP flags.
    for name in ('direct/hooks.c','hle.cpp','threaded.cpp'):
        cmds=[c for c in p.commands if c[-1].endswith('/'+name)]
        assert len(cmds)==1
        cmds[0][-1:-1]=['-flto','-fno-fat-lto-objects']
    p.link.insert(1,'-flto=1')
if '--audio-budget' in sys.argv:
    audio=(RUNTIME/'audio_boot.c').read_text()
    k='void ngb_audio_poll(void)';assert audio.count(k)==1
    audio=audio.replace(k,'static void original_audio_poll(void)')+Path(__file__).with_name('audio-budget.inc').read_text()
    ix=[i for i,v in enumerate(p.link) if v.endswith('/audio_boot.c.o')]
    assert len(ix)==1
    p.link[ix[0]]=p.compile('audio_boot.c',audio)
    src=src.replace('void __real_ngb_kernel_log','extern void audio_budget_flip(unsigned); void phase_flip(unsigned f){audio_budget_flip(f); }\nvoid __real_ngb_kernel_log',1)
if '--light-budget' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('light-budget.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--light-path' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('light-path.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--light-count' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('light-count.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--row-reasons' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('row-reasons.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--row-bins' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('row-bins.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--matrix-budget' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('matrix-budget.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--contact-budget' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('matrix-budget.inc').read_text().replace('MATRIX_BUDGET','CONTACT_BUDGET')+'\nvoid __real_ngb_kernel_log',1)
if '--copy-coverage' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('copy-coverage.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--fifo-groups' in sys.argv:
    import runpy
    cc=runpy.run_path(str(Path(__file__).with_name('fifo-groups.py')))
    nv=cc['transform']((RUNTIME/'nv2a_boot.c').read_text())
    ix=[i for i,v in enumerate(p.link) if v.endswith('/nv2a_boot.c.o')];assert len(ix)==1
    p.link[ix[0]]=p.compile('nv2a_boot.c',nv)
    src=src.replace('void __real_ngb_kernel_log',cc['counters']+'\nvoid __real_ngb_kernel_log',1)
if '--clock-census' in sys.argv:
    import runpy
    cc=runpy.run_path(str(Path(__file__).with_name('clock-census.py')))
    nv=cc['transform']((RUNTIME/'nv2a_boot.c').read_text())
    ix=[i for i,v in enumerate(p.link) if v.endswith('/nv2a_boot.c.o')];assert len(ix)==1
    p.link[ix[0]]=p.compile('nv2a_boot.c',nv)
    src=src.replace('void __real_ngb_kernel_log',cc['counters']+'\nvoid __real_ngb_kernel_log',1)
if '--mesh-paths' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',(Path(__file__).with_name('tree-pair-cost.inc').read_text().replace('[2]', '[6]' if '--material-op-cost' in sys.argv else '[4]' if '--material-callback-cost' in sys.argv else '[18]').replace('i<2','i<6' if '--material-op-cost' in sys.argv else 'i<4' if '--material-callback-cost' in sys.argv else 'i<18') if '--mesh-cost' in sys.argv else Path(__file__).with_name('mesh-key-paths.inc' if '--mesh-key-paths' in sys.argv else 'mesh-paths.inc').read_text())+'\nvoid __real_ngb_kernel_log',1)
    if '--material-op-cost' in sys.argv:
        k='void phase_flip(unsigned f){'
        assert src.count(k)==1
        src=src.replace(k,Path(__file__).with_name('material-op-target.inc').read_text()+k+'mc_flip(f);')
elif '--tree-pair-cost' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',(Path(__file__).with_name('tree-pair-cost.inc').read_text().replace('[2]', '[20]').replace('i<2','i<20') if set(sys.argv)&{'--shader-child','--script-arm-cost'} else Path(__file__).with_name('tree-pair-cost.inc').read_text().replace('[2]', '[7]').replace('i<2','i<7') if '--tree-draw-cost' in sys.argv else Path(__file__).with_name('tree-pair-cost.inc').read_text())+'\nvoid __real_ngb_kernel_log',1)
if {'--task298-cost','--task200-cost','--task2ae-cost'} & set(sys.argv):
    size=25 if '--task2ae-cost' in sys.argv else 26 if '--task200-cost' in sys.argv else 12
    a=src.index('unsigned tree_epoch=');b=src.index('void __real_ngb_kernel_log',a)
    inc=src[a:b].replace('tc_rng=233,','').replace('[2]', f'[{size}]').replace('i<2',f'i<{size}')
    x=inc.index('tc_calls[i]++;');y=inc.index('return 0;',inc.index('if(k==1)',x))
    inc=inc[:x]+'tc_calls[i]++;unsigned long long t=tc_clock();tc_blank[i]+=tc_clock()-t;tc_blanks[i]++;return tc_clock();'+inc[y+9:]
    src=src[:a]+inc+src[b:]
if '--tree-triple' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('tree-triple.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--mixed-hit' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('mixed-hit.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--mixed-span' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('mixed-span.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--axis-parent' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('axis-parent.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--axis-query' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('axis-query.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--actor-tree' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('actor-tree.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--actor-values' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('actor-values.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--actor-table' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('actor-table.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--node-budget' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('node-budget.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--node-prefix' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('node-prefix.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--family-budget' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('family-budget.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--node-family' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',r'''unsigned nf_active,nf_used,nf_rows[1024][6];
void phase_flip(unsigned f){
 if(nf_active){fprintf(stderr,"[NODE_FAMILY] %u %u",f,nf_used);
 for(unsigned i=0;i<nf_used&&i<1024;i++)fprintf(stderr," %u:%x:%x:%u:%x:%x",nf_rows[i][0],nf_rows[i][1],nf_rows[i][2],nf_rows[i][3],nf_rows[i][4],nf_rows[i][5]);
 fputc(10,stderr);}
 nf_active=(f==0||f==29||f==30||f==59||f==89||f==119);
 nf_used=0;if(nf_active)memset(nf_rows,0,sizeof nf_rows);
}
void __real_ngb_kernel_log''',1)
if '--node-order' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',r'''unsigned no_active,no_used,no_rows[256][4];
void phase_flip(unsigned f){
 if(no_active){fprintf(stderr,"[NODE_ORDER] %u %u",f,no_used);
 for(unsigned i=0;i<no_used&&i<256;i++)fprintf(stderr," %x:%x:%u:%x",no_rows[i][0],no_rows[i][1],no_rows[i][2],no_rows[i][3]);
 fputc(10,stderr);}
 no_active=(f==0||f==29||f==30||f==59||f==89||f==119);
 no_used=0;if(no_active)memset(no_rows,0,sizeof no_rows);
}
void __real_ngb_kernel_log''',1)
if '--node-census' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',r'''unsigned nc_active,nc_tab[4096][3],nc_counts[6];
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[NODE_CENSUS] %u %u %u %u %u %u %u\n",f,nc_counts[0],nc_counts[1],nc_counts[2],nc_counts[3],nc_counts[4],nc_counts[5]);
 if(!f||f==30)memset(nc_counts,0,sizeof nc_counts);
 memset(nc_tab,0,sizeof nc_tab);
 nc_active=f<120;
}
void __real_ngb_kernel_log''',1)
if '--vm-block-census' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned vb_active;unsigned long long vb_bins[5];
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[VB_CENSUS] %u %llu %llu %llu %llu %llu\n",f,vb_bins[0],vb_bins[1],vb_bins[2],vb_bins[3],vb_bins[4]);
 if(!f||f==30){memset(vb_bins,0,sizeof vb_bins);}
 vb_active=f<120;
}
void __real_ngb_kernel_log''',1)
if '--sync-budget' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('sync-budget.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--after-regs' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('after-regs.py')))['install'](p,RUNTIME,'--simple-literal' in sys.argv,'--constant-groups' in sys.argv,'--sync-budget' in sys.argv,'--light-before' in sys.argv,'--rs-prefix' in sys.argv,'--scope-floor' in sys.argv,'--push-scratch' in sys.argv,'--program-range' in sys.argv)
if '--hle-scalar-call' in sys.argv:
    assert '--after-regs' in sys.argv
    runpy.run_path(str(Path(__file__).with_name('hle-scalar-call.py')))['install'](p,RUNTIME)
if '--native-draw-o3' in sys.argv:
    # The original host command contains -O3 followed by -O2; only replace
    # its final level, and only in the two units actually rebuilt below.
    for name in ('threaded.cpp','hle.cpp'):
        hits=[c for c in p.commands if c[-1].endswith('/'+name)]
        assert len(hits)==1
        c=hits[0];levels=[j for j,arg in enumerate(c) if arg in ('-O0','-O1','-O2','-O3','-Os')]
        assert c[levels[-1]]=='-O2' and '-ffast-math' not in c
        c[levels[-1]]='-O3'
    p.add('hle.cpp',(RUNTIME.parents[2]/'src/d3d/hle.cpp').read_text())
if '--vblank-window' in sys.argv:
    import runpy
    obj=p.compile('nv2a_boot.c',runpy.run_path(str(Path(__file__).with_name('vblank-window.py')))['transform']((RUNTIME/'nv2a_boot.c').read_text()))
    hits=[i for i,v in enumerate(p.link) if v.endswith('/nv2a_boot.c.o')]
    assert len(hits)==1
    p.link[hits[0]]=obj
if {'--fifo-last-state','--fifo-lookahead','--fifo-method-table'} & set(sys.argv):
    import runpy
    obj=p.compile('nv2a_boot.c',runpy.run_path(str(Path(__file__).with_name('fifo-last-state.py' if '--fifo-last-state' in sys.argv else 'fifo-method-table.py' if '--fifo-method-table' in sys.argv else 'fifo-lookahead.py')))['transform']((RUNTIME/'nv2a_boot.c').read_text()))
    hits=[i for i,v in enumerate(p.link) if v.endswith('/nv2a_boot.c.o')]
    assert len(hits)==1
    p.link[hits[0]]=obj
if '--command-record' in sys.argv:
    import runpy
    t=(RUNTIME.parents[2]/'src/d3d/gpu/threaded.cpp').read_text()
    if '--ps-range-epoch' in sys.argv:
        psr=runpy.run_path(str(Path(__file__).with_name('pixel-range-epoch.py')))
        assert p.link.count(str(p.out/'hle.cpp.o'))==1
        p.compile('hle.cpp',psr['hle']((p.out/'hle.cpp').read_text()))
        t=psr['recorder'](t)
    if '--material-pieces' in sys.argv:
        t=runpy.run_path(str(Path(__file__).with_name('material-pieces.py')))['transform'](t)
    if '--four-piece' in sys.argv:
        t=runpy.run_path(str(Path(__file__).with_name('four-piece.py')))['transform'](t)
    if '--strip-snapshot-join' in sys.argv:
        t=runpy.run_path(str(Path(__file__).with_name('strip-snapshot-join.py')))['transform'](t)
    if '--draw-separation' in sys.argv:
        t=runpy.run_path(str(Path(__file__).with_name('draw-separation.py')))['transform'](t,'--draw-shader-detail' in sys.argv,'--strip-reason' in sys.argv,'--strip-footprint' in sys.argv)
        src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('draw-separation.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
    elif '--range-census' in sys.argv:
        t=runpy.run_path(str(Path(__file__).with_name('range-census.py')))['transform'](t)
        src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('range-census.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
    if '--delta-gap' in sys.argv:
        t=runpy.run_path(str(Path(__file__).with_name('delta-gap.py')))['transform'](t)
        src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('delta-gap.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
    if '--snapshot-budget' in sys.argv:
        t=runpy.run_path(str(Path(__file__).with_name('snapshot-budget.py')))['transform'](t)
        src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('snapshot-budget.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
    if '--index-origin' in sys.argv:
        hs=runpy.run_path(str(Path(__file__).with_name('index-origin.py')))
        assert p.link.count(str(p.out/'hle.cpp.o')) == 1
        p.compile('hle.cpp',hs['tag_hle']((p.out/'hle.cpp').read_text()))
        t=hs['transform'](t)
        src=src.replace('void __real_ngb_kernel_log',hs['counters']()+'\nvoid __real_ngb_kernel_log',1)
    if '--header-sets' in sys.argv:
        hs=runpy.run_path(str(Path(__file__).with_name('header-sets.py')))
        t=hs['transform'](t)
        src=src.replace('void __real_ngb_kernel_log',hs['counters']+'\nvoid __real_ngb_kernel_log',1)
    if '--blend-palette' in sys.argv:
        v=(RUNTIME.parents[2]/'src/d3d/vk/backend.cpp').read_text()
        transform=runpy.run_path(str(Path(__file__).with_name('blend-palette.py')))['transform']
        v=transform(v).replace('const bool two = fk.blend == 1;', '''static const bool control=std::getenv("NGB_PALETTE_CONTROL")!=nullptr;
            static bool seen=false;if(!seen && fk.blend==1){seen=true;std::fprintf(stderr,"[PALETTE] mode1 control=%d\\n",int(control));}
            const bool two = !control && fk.blend == 1;''')
        p.link[p.link.index(str(REGS/'backend-host-clip.o'))]=p.compile('vk/backend.cpp',v,['-DNGB_RIGID_CLIP'])
    if '--title-pipeline-prep' in sys.argv:
        assert '--title-worker-prep' in sys.argv and '--pipeline-wait' not in sys.argv
        v=(RUNTIME.parents[2]/'src/d3d/vk/backend.cpp').read_text()
        apply=runpy.run_path(str(Path(__file__).with_name('title-pipeline-prep.py')))['apply']
        if '--clip-record-cost' in sys.argv:
            cr=runpy.run_path(str(Path(__file__).with_name('clip-record-cost.py')))
            t=cr['recorder'](t);v=cr['backend'](v)
        p.link[p.link.index(str(REGS/'backend-host-clip.o'))]=p.compile('vk/backend.cpp',runpy.run_path(str(Path(__file__).with_name('title-pipeline-prep.py')))['instrument_first_use'](apply(v)) if '--cold-cost' in sys.argv else runpy.run_path(str(Path(__file__).with_name('draw-neighbors.py')))['apply'](apply(v),'--geom-neighbors' in sys.argv,'--bias-neighbors' in sys.argv) if '--draw-neighbors' in sys.argv else apply(v),['-DNGB_RIGID_CLIP'])
    if '--pipeline-wait' in sys.argv:
        pw=runpy.run_path(str(Path(__file__).with_name('pipeline-wait.py')))
        t=pw['wait'](t)
        v=(RUNTIME.parents[2]/'src/d3d/vk/backend.cpp').read_text()
        p.link[p.link.index(str(REGS/'backend-host-clip.o'))]=p.compile('vk/backend.cpp',pw['backend'](v),['-DNGB_RIGID_CLIP'])
        src=src.replace('void __real_ngb_kernel_log',pw['counters']+'\nvoid __real_ngb_kernel_log',1)
    if '--wait-origin' in sys.argv:
        wo=runpy.run_path(str(Path(__file__).with_name('wait-origin.py')))
        t=wo['transform'](t)
        src=src.replace('void __real_ngb_kernel_log',wo['counters']+'\nvoid __real_ngb_kernel_log',1)
    if '--header-words' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('header-words.py')))['transform'](t)
    if '--header-fold' in sys.argv:
        assert t.count('recent_[(header >> 4) & 63]')==2 and t.count('Recent recent_[64]')==1
        t=t.replace('recent_[(header >> 4) & 63]','recent_[((header >> 4) ^ (header >> 12)) & 255]').replace('Recent recent_[64]','Recent recent_[256]')
    if '--batch-handoff' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('batch-handoff.py')))['transform'](t)
    if '--batch-index-owner' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('batch-index-owner.py')))['transform'](t)
    if '--consumer-bounds' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('consumer-bounds.py')))['transform'](t)
    if '--index-prefetch' in sys.argv:
        k='        SendState(s, start + count);'
        assert t.count(k)==1
        t=t.replace(k, """#ifdef NGB_DIRECT3D
        if (indices && count >= 64 && count <= 4096) {
            uintptr_t key = reinterpret_cast<uintptr_t>(indices);
            const auto& slot = index_slots_[((key >> 2) ^ (key >> 13) ^ count) & 2047];
            __builtin_prefetch(indices, 0, 1);
            __builtin_prefetch(indices + 64, 0, 1);
            if (slot.source == indices && slot.count == count && slot.snapshot) {
                const auto* saved = slot.snapshot->bytes.data();
                __builtin_prefetch(saved, 0, 1);
                __builtin_prefetch(saved + 64, 0, 1);
            }
        }
#endif
"""+k)
    if '--group-copy' in sys.argv:
        k='            size_t limit = off + group, first = off;'
        assert t.count(k)==1
        t=t.replace(k, """            if (group > kPiece) {
                WriteDelta(off, now, group);
                off += group;
                continue;
            }
"""+k)
    if '--rs-prefix' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('rs-prefix.py')))['threaded'](t)
    if '--delta-adjacent' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('delta-adjacent.py')))['transform'](t)
    if '--known-difference' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('known-difference.py')))['transform'](t)
    if '--state-witness' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('state-witness.py')))['transform'](t)
    if '--copy-index-batch' in sys.argv:
        old='if (count < 64 || count > 4096) return {};'
        assert t.count(old)==1
        t=t.replace(old,'if (count != 64) return {};')
    if '--index-equal' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('index-equal.py')))['transform'](t)
    if '--header-span' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('header-span.py')))['transform'](t)
    if '--batch-128' in sys.argv:
        previous='constexpr uint32_t kBatchCommands = 64;'
        assert t.count(previous)==1 and t.count('kBatchCommands')==2
        t=t.replace(previous,previous.replace('64','128'))
    if '--batch-headers' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('batch-headers.py')))['transform'](t)
    if '--fixed-mask-packet' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('fixed-mask-packet.py')))['transform'](t)
    if '--batch-bytes' in sys.argv: t=runpy.run_path(str(Path(__file__).with_name('batch-bytes.py')))['transform'](t)
    p.add('threaded.cpp',runpy.run_path(str(Path(__file__).with_name('command-record.py')))['transform'](t))
if '--fixed-pieces' in sys.argv:
    t=(RUNTIME.parents[2]/'src/d3d/gpu/threaded.cpp').read_text()
    start='    template<size_t I>\n    void SendFixedRange('
    call='else SendRange(now, r);'
    assert t.count(start)==t.count(call)==1
    p.add('threaded.cpp',t.replace(start,Path(__file__).with_name('fixed-pieces.inc').read_text()+start).replace(call,'else ChangedFixedRange<I>(now);'))
if '--owner-recorder' in sys.argv:
    import runpy
    t=(RUNTIME.parents[2]/'src/d3d/gpu/threaded.cpp').read_text()
    p.add('threaded.cpp',runpy.run_path(str(Path(__file__).with_name('owner-recorder.py')))['transform'](t))
if '--hle-leaf' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('hle-leaf.py')))['install'](p,REGS,False)
if set(sys.argv)&{'--cmd-page-run','--cmd-pointer','--box-inline','--cmd-budget','--cmd-pass','--box-budget','--box-scan','--box-reuse','--page-shape','--contact-repeat','--contact-blocks','--frame-pc','--full-guest','--full-page','--compact-bridges','--matrix-row','--memory-census','--hot-image-span','--word-page','--byte-page','--span-audit','--frame-spans','--shader-bank','--hot-entry','--guest-frame','--transform-guard','--contact-axis','--detail-cost','--command-record','--fixed-pieces','--index-dispatch','--jump-buckets','--checkpoint-leaf','--irq-cost','--empty-material','--vector-span','--scalar-run','--scalar-all','--product-cache','--round-range','--stage-tail','--matrix-transfer','--fist-round'}:
    variant=p.core/('opening-full-page' if '--full-page' in sys.argv else 'opening-full-guest')
    if '--full-page' in sys.argv:
        for name in ('vm.c','contiguous.c'):
            mapped=(variant/name).read_text()
            if {'--stack-outline','--stack-prefix'} & set(sys.argv) and name=='vm.c':
                import runpy
                mapped=runpy.run_path(str(Path(__file__).with_name('stack-prefix.py')))['vm'](mapped)
            if '--low-words' in sys.argv and name=='vm.c':
                import runpy
                mapped=runpy.run_path(str(Path(__file__).with_name('low-words.py')))['vm'](mapped)
            if '--low-prefix-sample' in sys.argv and name=='vm.c':
                import runpy
                mapped=runpy.run_path(str(Path(__file__).with_name('low-prefix-sample.py')))['vm'](mapped)
            if {'--vm-blocks','--vm-block-census'} & set(sys.argv) and name=='vm.c':
                import runpy
                mapped=runpy.run_path(str(Path(__file__).with_name('vm-blocks.py')))['vm'](mapped)
            if '--guard-host' in sys.argv: mapped=runpy.run_path(str(Path(__file__).with_name('guard-view.py')))['mapping'](mapped)
            obj=p.compile(name,mapped)
            ix=[i for i,x in enumerate(p.link) if x.endswith('/'+name+'.o')]
            if ix:
                assert len(ix)==1
                p.link[ix[0]]=obj
            else:p.link.insert(1,obj)
    for u in range(47):
        n=f'recomp_{u:04}'
        hits=[i for i,t in enumerate(p.link) if t.endswith(('/'+n+'.o','/'+n+'.c.o'))]
        assert len(hits)==1,(n,hits)
        p.link[hits[0]]=str(variant/(n+'.c.o'))
    for n in ('entry.o','gates.o'):p.link[p.link.index(str(REGS/n))]=str(variant/n)
if '--paired-entry-slots' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('paired-entry-slots.py')))['install'](p,variant)
if '--scope-floor' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('scope-floor.py')))['gate'](p,variant)
if '--alloc-budget' in sys.argv:
    import runpy
    ab=runpy.run_path(str(Path(__file__).with_name('alloc-budget.py')))
    p.link[1:1]=['-Wl,'+','.join('--wrap='+op[0] for op in ab['ops'])]
    src=src.replace('void __real_ngb_kernel_log',ab['instrument']()+'\nvoid __real_ngb_kernel_log',1)
if '--bulk-budget' in sys.argv:
    p.link[1:1]=['-Wl,--wrap=memcpy,--wrap=memmove,--wrap=memset']
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('bulk-budget.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--gate-pairs' in sys.argv:
    import subprocess
    asm=p.out/'gate-pairs.s';gate=(variant/'gates.s').read_text()
    key='ngb_gate_indirect:\n';assert gate.count(key)==1
    asm.write_text(gate.replace(key,key+Path(__file__).with_name('gate-pairs.s.inc').read_text()))
    obj=asm.with_suffix('.o');subprocess.run(['cc','-c',asm,'-o',obj],check=True)
    p.link[p.link.index(str(variant/'gates.o'))]=str(obj)
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('gate-pairs.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--public-entry' in sys.argv:
    import runpy
    pe=runpy.run_path(str(Path(__file__).with_name('public-entry.py')))['install'](p,variant)
    src=src.replace('void __real_ngb_kernel_log',pe+'\nvoid __real_ngb_kernel_log',1)
if '--pointer-sites' in sys.argv:
    import subprocess
    g=(variant/'gates.s').read_text()
    k=' bl ngb_guest_pointer\n'
    assert g.count(k)==1
    g=g.replace(k,' mov x2,x30\n bl pointer_site_resolve\n')
    asm=p.out/'pointer-site.s';asm.write_text(g)
    o=asm.with_suffix('.o');subprocess.run(['cc','-c',asm,'-o',o],check=True)
    p.link[p.link.index(str(variant/'gates.o'))]=str(o)
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('pointer-sites.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if {'--gate-mapped','--gate-high','--gate-pointer'} & set(sys.argv):
    import runpy
    runpy.run_path(str(Path(__file__).with_name('gate-pointer.py')))['install'](p,variant,'--gate-high' in sys.argv,'--gate-census' in sys.argv,'--gate-mapped' in sys.argv)
if '--light-stages' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-light-stages'/obj)
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('light-stages.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--tree-census' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-tree-census'/obj)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned tree_active,tree_nodes,tree_nulls,tree_over,tree_n[64],tree_va[64];
void phase_flip(unsigned f){
 if(f==30||f==120){fprintf(stderr,"[TREE_CENSUS] %u nodes=%u null=%u overflow=%u",f,tree_nodes,tree_nulls,tree_over);
 for(unsigned i=0;i<64&&tree_n[i];i++){fprintf(stderr," %08x:%u",tree_va[i],tree_n[i]);}fputc(10,stderr);}
 if(!f||f==30){tree_nodes=tree_nulls=tree_over=0;memset(tree_n,0,sizeof tree_n);}tree_active=f<120;
}
void __real_ngb_kernel_log''',1)
if '--tree-null' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-tree-null'/obj)
if '--light-clear' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-light-clear'/obj)
if '--poll-inline' in sys.argv:
    for u in (0,28):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-poll-inline'/obj)
if '--light-budget' in sys.argv:
    obj='recomp_0044.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-light-budget'/obj)
if '--light-path' in sys.argv:
    obj='recomp_0044.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-light-path'/obj)
if '--light-count' in sys.argv:
    obj='recomp_0044.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-light-count'/obj)
if '--copy-coverage' in sys.argv:
    obj='recomp_0044.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-copy-coverage'/obj)
if '--light-record' in sys.argv:
    obj='recomp_0044.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-light-record'/obj)
if '--light-zero' in sys.argv:
    obj='recomp_0044.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-light-zero'/obj)
if '--material-inline' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-material-inline'/obj)
if '--tree-tickets' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-tree-tickets'/obj)
if '--row-three' in sys.argv:
    obj='recomp_0027.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-row-three'/obj)
if '--tree-dispatch' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-tree-dispatch'/obj)
if '--tree-level' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-tree-level'/obj)
if '--page-hot-o3' in sys.argv:
    assert '--full-page' in sys.argv
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-page-hot-o3'/obj)
if '--vm-block-census' in sys.argv:
    assert '--page-hot-o3' in sys.argv
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-page-hot-o3'/obj))]=str(p.core/'opening-vm-block-census'/obj)
if '--vm-blocks' in sys.argv:
    assert '--page-hot-o3' in sys.argv
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-page-hot-o3'/obj))]=str(p.core/'opening-vm-blocks'/obj)
if '--unordered-branch' in sys.argv:
    assert '--page-hot-o3' in sys.argv
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-page-hot-o3'/obj))]=str(p.core/'opening-unordered-branch'/obj)
if '--loop-ira' in sys.argv:
    assert '--page-hot-o3' in sys.argv
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-page-hot-o3'/obj))]=str(p.core/'opening-loop-ira'/obj)
if '--compact-loops' in sys.argv:
    assert '--page-hot-o3' in sys.argv
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-page-hot-o3'/obj))]=str(p.core/'opening-compact-loops'/obj)
if '--simple-layout' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-simple-layout'/obj)
if '--page-bias' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-page-bias'/obj)
if '--reg-base' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-reg-base'/obj)
if '--cmd-target' in sys.argv:
    obj='recomp_0010.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-cmd-target'/obj)
if '--node-walk' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-node-walk'/obj)
if '--node-page-run' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-node-page-run'/obj)
if '--node-census' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-node-census'/obj)
if '--family-budget' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-family-budget'/obj)
if '--node-family' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-node-family'/obj)
if '--node-order' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-node-order'/obj)
if '--node-prefix' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-node-prefix'/obj)
if '--object-shift' in sys.argv:
    obj='recomp_0001.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-object-shift'/obj)
if '--ordered-branch' in sys.argv or '--ordered-control' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/('opening-ordered-branch' if '--ordered-branch' in sys.argv else 'opening-ordered-control')/obj)
elif '--mesh-paths' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/('opening-mesh-expensive-target' if '--mesh-expensive-target' in sys.argv else 'opening-mesh-expensive-setup' if '--mesh-expensive-setup' in sys.argv else 'opening-mesh-common-setup' if '--mesh-common-setup' in sys.argv else 'opening-mesh-common-cost' if '--mesh-common-cost' in sys.argv else 'opening-mesh-expensive-cost' if '--mesh-expensive-cost' in sys.argv else 'opening-setup-cost' if '--setup-cost' in sys.argv else 'opening-material-op-cost' if '--material-op-cost' in sys.argv else 'opening-material-callback-cost' if '--material-callback-cost' in sys.argv else 'opening-mesh-cost' if '--mesh-cost' in sys.argv else 'opening-mesh-key-paths' if '--mesh-key-paths' in sys.argv else 'opening-mesh-paths')/obj)
elif '--task200-cost' in sys.argv:
    obj='recomp_0000.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-task200-cost'/obj)
elif '--task298-cost' in sys.argv or '--task2ae-cost' in sys.argv:
    obj='recomp_0001.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/('opening-task2ae-cost' if '--task2ae-cost' in sys.argv else 'opening-task298-cost')/obj)
elif '--script-loop-cost' in sys.argv:
    obj='recomp_0000.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-script-loop-cost'/obj)
elif '--script-arm-cost' in sys.argv:
    obj='recomp_0000.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-script-arm-cost'/obj)
elif '--tree-pair-cost' in sys.argv and '--select-split' not in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/('opening-shader-child' if '--shader-child' in sys.argv else 'opening-tree-draw-cost' if '--tree-draw-cost' in sys.argv else 'opening-tree-pair-cost')/obj)
if '--tree-triple' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-tree-triple'/obj)
if '--superblocks' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-superblocks'/obj)
if '--vector-end-page' in sys.argv:
    for u in (2,10,16,28,29):
        obj=f'recomp_{u:04}.c.o'
        before=p.core/'opening-compact-loops' if u in (2,10,16) else variant
        p.link[p.link.index(str(before/obj))]=str(p.core/'opening-vector-end-page'/obj)
if '--vector-load-lane' in sys.argv:
    for u in (0,28,29):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-vector-load-lane'/obj)
if '--stack-two-words' in sys.argv:
    for u in (1,9,15):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-stack-two-words'/obj)
if '--stack-long-run' in sys.argv:
    for u in (1,9,15):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-stack-long-run'/obj)
if '--affine-local' in sys.argv:
    obj='recomp_0000.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-affine-local'/obj)
if '--paired-copy' in sys.argv:
    obj='recomp_0044.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-paired-copy'/obj)
if '--call-stack' in sys.argv:
    for u in (2,16,0,28,29):
        obj=f'recomp_{u:04}.c.o'
        before=p.core/'opening-compact-loops' if u in (2,16) else variant
        p.link[p.link.index(str(before/obj))]=str(p.core/'opening-call-stack'/obj)
if '--rmw-flags' in sys.argv:
    for u in (2,16,1,9,29):
        obj=f'recomp_{u:04}.c.o'
        before=p.core/'opening-compact-loops' if u in (2,16) else variant
        p.link[p.link.index(str(before/obj))]=str(p.core/'opening-rmw-flags'/obj)
if '--low-words' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-low-words'/obj)
if '--indexed-read' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-indexed-read'/obj)
if '--predicate-edge' in sys.argv:
    for u in (2,):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-predicate-edge'/obj)
if '--stack-outline' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-stack-outline'/obj)
if '--stack-prefix' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-stack-prefix'/obj)
if '--word-site-census' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',('#define WS_EXACT_ADDRESS 1\n' if '--word-address-census' in sys.argv else '')+Path(__file__).with_name('word-runs.inc' if '--word-runs' in sys.argv else 'table-locality.inc' if '--table-locality' in sys.argv else 'word-eligibility.inc' if '--word-eligibility' in sys.argv else 'word-site-census.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-word-site-census'/obj)
if '--stack-window' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('stack-window.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-stack-window'/obj)
if '--target-hist' in sys.argv:
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('target-hist.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
    for u in (0,2):
        obj=f'recomp_{u:04}.c.o'
        before=variant if u==0 else p.core/'opening-compact-loops'
        p.link[p.link.index(str(before/obj))]=str(p.core/'opening-target-hist'/obj)
if '--target-switch' in sys.argv:
    for u in (0,2):
        obj=f'recomp_{u:04}.c.o'
        before=variant if u==0 else p.core/'opening-compact-loops'
        p.link[p.link.index(str(before/obj))]=str(p.core/'opening-target-switch'/obj)
if '--icall-local' in sys.argv:
    for u in (2,10,16,26,39,28):
        obj=f'recomp_{u:04}.c.o'
        before=variant if u==28 else p.core/'opening-compact-loops'
        p.link[p.link.index(str(before/obj))]=str(p.core/'opening-icall-local'/obj)
if '--mesh-edges' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-mesh-edges'/obj)
if '--material-span' in sys.argv:
    obj='recomp_0044.c.o'
    p.link[p.link.index(str(p.core/'opening-paired-copy'/obj))]=str(p.core/'opening-material-span'/obj)
if '--cmd-service-span' in sys.argv:
    obj='recomp_0010.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-cmd-service-span'/obj)
if '--shared-pop-tail' in sys.argv:
    for u in (2,10,16,26):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-shared-pop-tail'/obj)
if '--guard-view' in sys.argv:
    assert '--guard-host' in sys.argv
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-guard-view'/obj)
if '--alias-words' in sys.argv:
    assert '--alias-host' in sys.argv
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-alias-words'/obj)
if '--material-compare-chain' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-material-compare-chain'/obj)
if '--mesh-stage' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-mesh-stage'/obj)
if '--mesh-trace' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-mesh-trace'/obj)
if '--model-copy' in sys.argv:
    for u in (16,28,29):
        obj=f'recomp_{u:04}.c.o'
        before=p.core/'opening-compact-loops' if u==16 else variant
        p.link[p.link.index(str(before/obj))]=str(p.core/'opening-model-copy'/obj)
if '--slot-copy' in sys.argv:
    obj='recomp_0005.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-slot-copy'/obj)
if '--material-twin' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-material-twin'/obj)
if '--return-store' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-return-store'/obj)
if '--row-reasons' in sys.argv:
    obj='recomp_0039.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-row-reasons'/obj)
if '--row-bins' in sys.argv:
    obj='recomp_0039.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-row-bins'/obj)
if '--matrix-budget' in sys.argv:
    obj='recomp_0039.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-matrix-budget'/obj)
if '--contact-budget' in sys.argv:
    obj='recomp_0010.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-contact-budget'/obj)
if '--row-range' in sys.argv:
    obj='recomp_0039.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-row-range'/obj)
if '--row-ceiling' in sys.argv:
    obj='recomp_0039.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-row-ceiling'/obj)
if '--size-hot' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-size-hot'/obj)
if '--effective-mask' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-effective-mask'/obj)
    rt=(p.out/'host-runtime.inc').read_text()
    for anchor,addition in (
        ('unsigned ngb_pending_dpcs;', 'unsigned ngb_effective_mask=3; void ngb_refresh_effective_mask(void){ngb_effective_mask=ngb_pending_dpcs ? 0u : ngb_poll_mask;}'),
        ('--ngb_pending_dpcs * sizeof(*dpc_queue));', 'ngb_refresh_effective_mask();'),
        ('dpc_queue[ngb_pending_dpcs++] = object;', 'ngb_refresh_effective_mask();'),
        ('ngb_pending_dpcs = 0;', 'ngb_refresh_effective_mask();')):
        assert rt.count(anchor)==1,anchor
        rt=rt.replace(anchor,anchor+' '+addition)
    (p.out/'effective-mask-runtime.inc').write_text(rt)
    assert src.count('"host-runtime.inc"')==1
    src=src.replace('"host-runtime.inc"','"effective-mask-runtime.inc"')
    reset='    ngb_pending_dpcs = 0;'
    assert src.count(reset)==1
    src=src.replace(reset,reset+' ngb_refresh_effective_mask();')
if '--dispatch-domain' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-dispatch-domain'/obj)
if '--block-predicate' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-block-predicate'/obj)
if '--cold-scalar' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-cold-scalar'/obj)
if '--literal-xmm' in sys.argv:
    for u in (2,10,16,26):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-literal-xmm'/obj)
if '--matrix-four' in sys.argv:
    obj='recomp_0039.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-matrix-four'/obj)
if '--mixed-select' in sys.argv:
    for u in (10,16,26):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-mixed-select'/obj)
if '--mixed-fast' in sys.argv:
    for u in (2,10,16,26):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-mixed-fast'/obj)
if '--mixed-hit' in sys.argv:
    for u in (2,10,16,26):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-mixed-hit'/obj)
if '--mixed-span' in sys.argv:
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-mixed-span'/obj)
if '--axis-parent' in sys.argv:
    obj='recomp_0010.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-axis-parent'/obj)
if '--axis-query' in sys.argv:
    obj='recomp_0010.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-axis-query'/obj)
if '--actor-tree' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-actor-tree'/obj)
if '--actor-values' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-actor-values'/obj)
if '--actor-table' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-actor-table'/obj)
if '--node-budget' in sys.argv:
    obj='recomp_0016.c.o'
    p.link[p.link.index(str(p.core/'opening-compact-loops'/obj))]=str(p.core/'opening-node-budget'/obj)
if '--private-tail' in sys.argv:
    assert '--page-hot-o3' in sys.argv
    for u in (2,10,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(p.core/'opening-page-hot-o3'/obj))]=str(p.core/'opening-private-tail'/obj)
if '--compact-next' in sys.argv:
    assert '--full-page' in sys.argv
    for u in (28,1,0,29,15):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-compact-next'/obj)
if '--page-next-o3' in sys.argv:
    assert '--full-page' in sys.argv
    for u in (28,1,0,29,15):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-page-next-o3'/obj)
if '--hot-entry' in sys.argv:
    for u in (0,2,10,16,27,28,29,37,44):
        n=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/n))]=str(p.core/'opening-hot-entry'/n)
if '--guest-frame' in sys.argv:
    for u in (0,2,27,28,44):
        n=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/n))]=str(p.core/'opening-guest-frame'/n)
if '--transform-guard' in sys.argv:
    for u in (10,28):
        n=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/n))]=str(p.core/'opening-transform-guard'/n)
if '--contact-axis' in sys.argv:
    n='recomp_0010.c.o'
    p.link[p.link.index(str(variant/n))]=str(p.core/'opening-contact-axis'/n)
if '--contact-repeat' in sys.argv:
    n='recomp_0010.c.o'
    p.link[p.link.index(str(variant/n))]=str(p.core/'opening-contact-repeat'/n)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned contact_frame,contact_n[4];
void phase_flip(unsigned f){if(f==30||f==120){fprintf(stderr,"[CONTACT_REPEAT] %u %u %u %u %u\n",f,contact_n[0],contact_n[1],contact_n[2],contact_n[3]);}
 if(!f||f==30){memset(contact_n,0,sizeof contact_n);}contact_frame=f<120?f+1:0;}
void __real_ngb_kernel_log''',1)
if '--contact-blocks' in sys.argv:
    n='recomp_0010.c.o'
    p.link[p.link.index(str(variant/n))]=str(p.core/'opening-contact-blocks'/n)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned contact_blocks[256];
void phase_flip(unsigned f){
 if(f==30||f==120){fprintf(stderr,"[CONTACT_BLOCKS] %u",f);for(int i=0;i<256;i++)fprintf(stderr," %u",contact_blocks[i]);fputc(10,stderr);}
 if(!f||f==30)memset(contact_blocks,0,sizeof contact_blocks);
}
void __real_ngb_kernel_log''',1)

if '--cmd-pass' in sys.argv:
    obj='recomp_0010.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-cmd-pass'/obj)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned cmd_frame,cmd_words[3][13];
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<3;i++){fprintf(stderr,"[CMD_PASS] %u %u",f,i);for(unsigned j=0;j<13;j++)fprintf(stderr," %u",cmd_words[i][j]);fputc('\n',stderr);}
 if(!f||f==30)memset(cmd_words,0,sizeof cmd_words);
 cmd_frame=f<120;
}
void __real_ngb_kernel_log''',1)

if '--cmd-budget' in sys.argv:
    obj='recomp_0010.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-cmd-budget'/obj)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned cmd_window,cmd_seq,cmd_samples;unsigned long long cmd_ticks;
unsigned long long cmd_cpu(void){struct timespec ts;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&ts))abort();return (unsigned long long)ts.tv_sec*1000000000ull+ts.tv_nsec;}
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[CMD_BUDGET] %u %u %u %llu\n",f,cmd_seq,cmd_samples,cmd_ticks);
 if(!f||f==30){cmd_seq=0;cmd_samples=0;cmd_ticks=0;}
 cmd_window=f<120?f+1:0;
}
void __real_ngb_kernel_log''',1)

if '--box-budget' in sys.argv:
    obj='recomp_0026.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-box-budget'/obj)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned box_window,box_runs[3];unsigned long long box_ticks[3];
unsigned long long box_cpu(void){struct timespec ts;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&ts))abort();return (unsigned long long)ts.tv_sec*1000000000ull+ts.tv_nsec;}
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<3;i++)fprintf(stderr,"[BOX_BUDGET] %u %u %u %llu\n",f,i,box_runs[i],box_ticks[i]);
 if(!f||f==30){memset(box_runs,0,sizeof box_runs);memset(box_ticks,0,sizeof box_ticks);}
 box_window=f<120?f+1:0;
}
void __real_ngb_kernel_log''',1)

if '--box-scan' in sys.argv:
    obj='recomp_0026.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-box-scan'/obj)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned scan_active,scan_n[3][3];
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<3;i++)fprintf(stderr,"[BOX_SCAN] %u %u %u %u %u\n",f,i,scan_n[i][0],scan_n[i][1],scan_n[i][2]);
 if(!f||f==30)memset(scan_n,0,sizeof scan_n);
 scan_active=f<120;
}
void __real_ngb_kernel_log''',1)

if '--box-reuse' in sys.argv:
    obj='recomp_0026.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-box-reuse'/obj)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned box_frame,box_n[5];
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[BOX_REUSE] %u %u %u %u %u %u\n",f,box_n[0],box_n[1],box_n[2],box_n[3],box_n[4]);
 if(!f||f==30){memset(box_n,0,sizeof box_n);}box_frame=f<120?f+1:0;
}
void __real_ngb_kernel_log''',1)

if '--page-shape' in sys.argv:
    for u in (2,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-page-shape'/obj)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned shape_active,shape_page[4];
uint64_t shape_counts[4][16];
void phase_flip(unsigned f){
 if(f==30||f==120){for(unsigned i=0;i<4;i++){fprintf(stderr,"[PAGE_SHAPE] %u %u",f,i);for(unsigned j=0;j<16;j++)fprintf(stderr," %llu",(unsigned long long)shape_counts[i][j]);fputc(10,stderr);}}
 if(!f||f==30)memset(shape_counts,0,sizeof shape_counts);
 memset(shape_page,255,sizeof shape_page);shape_active=f<120;
}
void __real_ngb_kernel_log''',1)

if '--memory-census' in sys.argv:
    for u in (2,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-memory-census'/obj)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned census_active;
uint64_t census_rows[4][7];
void census_flip(unsigned f){
 if(f==30||f==120){
  for(unsigned i=0;i<4;i++){
   fprintf(stderr,"[MEM_CENSUS] %u %u",f,i);
   for(unsigned j=0;j<7;j++)fprintf(stderr," %llu",(unsigned long long)census_rows[i][j]);
   fputc('\n',stderr);
  }
 }
 if(!f||f==30)memset(census_rows,0,sizeof census_rows);
 census_active=f<120;
}
void __real_ngb_kernel_log''',1)
if set(sys.argv)&{'--span-audit','--frame-spans'}:
    audit='--span-audit' in sys.argv
    for u in (2,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/('opening-span-audit' if audit else 'opening-frame-spans')/obj)
    if audit:
        src=src.replace('void __real_ngb_kernel_log',r'''
unsigned span_on;
uint64_t span_count[2];
void span_count_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[SPAN_COUNT] %u %llu %llu\n",f,(unsigned long long)span_count[0],(unsigned long long)span_count[1]);
 if(!f||f==30)span_count[0]=span_count[1]=0;
 span_on=f<120;
}
void __real_ngb_kernel_log''',1)
if '--product-cache' in sys.argv:
    obj='recomp_0029.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-product-cache'/obj)
    src=src.replace('void __real_ngb_kernel_log',r'''
unsigned product_audit,product_checked;
__attribute__((constructor)) static void prod_start(void){product_audit=getenv("NGB_PRODUCT_CHECK")!=NULL;}
__attribute__((destructor)) static void prod_end(void){if(product_audit)fprintf(stderr,"[PRODUCT_CHECK] %u\n",product_checked);}
void __real_ngb_kernel_log''',1)
if '--round-range' in sys.argv:
    for u in (0,8,29,44):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-round-range'/obj)
if '--fist-round' in sys.argv:
    for u in (1,16,37,44):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-fist-round'/obj)
if set(sys.argv)&{'--vector-span','--scalar-run','--scalar-all'}:
    for u in (16,28,29):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/('opening-scalar-run' if set(sys.argv)&{'--scalar-run','--scalar-all'} else 'opening-vector-span')/obj)
if '--matrix-transfer' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-matrix-transfer'/obj)
if '--stage-tail' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-stage-tail'/obj)
if '--empty-material' in sys.argv:
    obj='recomp_0028.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-empty-material'/obj)
if '--history-cost' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('history-cost.py')))['install'](p,REGS)
if '--entry-mask' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('entry-mask.py')))['install'](p,REGS)
if '--entry-stream' in sys.argv:
    import runpy
    assert '--guest-sites' not in sys.argv or '--full-page' in sys.argv
    runpy.run_path(str(Path(__file__).with_name('entry-stream.py')))['install'](p,REGS,'--guest-sites' in sys.argv)
    src=src.replace('void __real_ngb_kernel_log',Path(__file__).with_name('inverse-inputs.inc' if '--inverse-inputs' in sys.argv else 'guest-sites.inc' if '--guest-sites' in sys.argv else 'entry-stream.inc').read_text()+'\nvoid __real_ngb_kernel_log',1)
if '--checkpoint-pack' in sys.argv:
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('checkpoint-pack.py')))['install'](p,REGS,src)
if '--checkpoint-loads' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('checkpoint-loads.py')))['install'](p,REGS)
if '--checkpoint-leaf' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('checkpoint-leaf.py')))['install'](p,REGS)
if '--index-dispatch' in sys.argv:
    for u in (0,2):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-index-dispatch'/obj)
if '--jump-buckets' in sys.argv:
    for u in (0,2):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-jump-buckets'/obj)
if '--cmd-page-run' in sys.argv:
    obj='recomp_0010.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-cmd-page-run'/obj)

if '--cmd-pointer' in sys.argv:
    obj='recomp_0010.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-cmd-pointer'/obj)

if '--box-inline' in sys.argv:
    obj='recomp_0026.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-box-inline'/obj)

if '--word-page' in sys.argv:
    for u in (2,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-word-page'/obj)
if '--byte-page' in sys.argv:
    for u in (2,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-byte-page'/obj)
if '--hot-image-span' in sys.argv:
    for u in (2,16,26,39):
        obj=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-hot-image-span'/obj)
if '--shader-bank' in sys.argv:
    import runpy
    transform=runpy.run_path(str(Path(__file__).with_name('shader-bank.py')))['transform']
    if '--draw-shader-detail' in sys.argv or '--strip-join-control' in sys.argv or '--strip-snapshot-join' in sys.argv:
        assert p.link.count(str(p.out/'hle.cpp.o'))==1
        p.compile('hle.cpp',transform((p.out/'hle.cpp').read_text()))
    else:
        p.add('hle.cpp',transform((RUNTIME.parents[2]/'src/d3d/hle.cpp').read_text()))
if '--pixel-write-plan' in sys.argv:
    import runpy
    h=(p.out/'hle.cpp').read_text() if str(p.out/'hle.cpp.o') in p.link else (RUNTIME.parents[2]/'src/d3d/hle.cpp').read_text()
    hs=runpy.run_path(str(Path(__file__).with_name('pixel-write-plan.py')))['transform'](h)
    if str(p.out/'hle.cpp.o') in p.link:p.compile('hle.cpp',hs)
    else:p.add('hle.cpp',hs)
if '--matrix-row' in sys.argv:
    obj='recomp_0039.c.o'
    p.link[p.link.index(str(variant/obj))]=str(p.core/'opening-matrix-row'/obj)
if '--compact-bridges' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('compact-bridges.py')))['install'](p)
if '--d3d-private' in sys.argv:
    import runpy,subprocess
    f=p.out/'d3d-private.S';o=f.with_suffix('.o')
    runpy.run_path(str(Path(__file__).with_name('d3d-private.py')))['generate'](Path('/work'),REGS,f)
    subprocess.run(['cc','-c',f,'-o',o],check=True)
    p.link[p.link.index(str(REGS/'gates.o'))]=str(o)
if set(sys.argv)&{'--vector-registers','--double-entry'}:
    variant=p.core/('opening-double-entry' if '--double-entry' in sys.argv else 'opening-vector-registers')
    for obj in [*REGS.glob('recomp_*.c.o'),REGS/'entry.o',REGS/'gates.o',REGS/'checkpoint.o']:
        p.link[p.link.index(str(obj))]=str(variant/obj.name)
if '--icall-train' in sys.argv or '--icall-direct' in sys.argv:
    train='--icall-train' in sys.argv
    variant=p.core/('opening-icall-train' if train else 'opening-icall-direct')
    for obj in [*REGS.glob('recomp_*.c.o'),REGS/'entry.o',REGS/'gates.o']:
        p.link[p.link.index(str(obj))]=str(variant/obj.name)
    if train:
        pre=Path(__file__).with_name('icall-train.inc').read_text()
        src=src.replace('void __real_ngb_kernel_log',pre+'\nvoid __real_ngb_kernel_log',1)
        tag='CHECK(sscanf(message,"3D scene flips=%u draws=%u",&flip,&draws)==2);'
        assert src.count(tag)==1
        src=src.replace(tag,tag+' icall_flip(flip);')
if set(sys.argv)&{'--indexed-image','--compact','--readonly','--readonly-audit','--stack-leaves','--fuse-hot','--opening-speed','--packed-ops'}:
    variant=p.core/('opening-indexed-image' if '--indexed-image' in sys.argv else 'opening-packed-ops' if '--packed-ops' in sys.argv else 'opening-speed' if '--opening-speed' in sys.argv else 'opening-fuse-hot' if '--fuse-hot' in sys.argv else 'opening-stack-leaves' if '--stack-leaves' in sys.argv else 'opening-compact-code' if '--compact' in sys.argv else 'opening-readonly-audit' if '--readonly-audit' in sys.argv else 'opening-readonly')
    for obj in [*REGS.glob('recomp_*.c.o'),REGS/'entry.o',REGS/'gates.o']:
        p.link[p.link.index(str(obj))]=str(variant/obj.name)
if '--register-ticket' in sys.argv:
    variant=p.core/'opening-register-ticket'
    for obj in [*REGS.glob('recomp_*.c.o'),REGS/'entry.o',REGS/'gates.o',REGS/'checkpoint.o']:
        p.link[p.link.index(str(obj))]=str(variant/obj.name)
if '--ticket' in sys.argv:
    variant=p.core/'opening-ticket'
    for obj in [*REGS.glob('recomp_*.c.o'),REGS/'entry.o',REGS/'gates.o']:
        p.link[p.link.index(str(obj))]=str(variant/obj.name)
    rt=(p.out/'host-runtime.inc').read_text()
    a='dpc_queue[ngb_pending_dpcs++] = object;'
    assert rt.count(a)==1
    rt='uint64_t ticket_deadline;\n'+rt.replace(a,a+' ticket_deadline=0;')
    (p.out/'ticket-runtime.inc').write_text(rt)
    assert src.count('"host-runtime.inc"')==1
    src=src.replace('"host-runtime.inc"','"ticket-runtime.inc"')
if set(sys.argv)&{'--page-limit','--literals','--region-bias','--stack-cache'}:
    literal='--literals' in sys.argv
    if literal:src='void ngb_literal_no_ram(void){__builtin_trap();}\n'+src
    variant=p.core/('opening-stack-cache' if '--stack-cache' in sys.argv else 'opening-image-literals' if literal else 'opening-region-bias' if '--region-bias' in sys.argv else 'opening-page-limit')
    for obj in [*REGS.glob('recomp_*.c.o'),REGS/'entry.o',REGS/'gates.o']:
        p.link[p.link.index(str(obj))]=str(variant/obj.name)
    for n in (() if literal else ('vm.c',) if '--stack-cache' in sys.argv else ('vm.c','contiguous.c')):
        o=p.compile(n,(variant/n).read_text())
        ix=[i for i,v in enumerate(p.link) if v.endswith('/'+n+'.o')]
        if ix:
            assert len(ix)==1
            p.link[ix[0]]=o
        else:p.link.insert(1,o)
if '--tree' in sys.argv:
    oo=REGS/'recomp_0028.c.o'
    p.link[p.link.index(str(oo))]=str(p.core/'opening-tree-loop'/oo.name)
    src='unsigned tree_loop_pick;\n#define cache_active tree_loop_pick\n'+src
if '--whole' in sys.argv:
    t=(RUNTIME.parents[2]/'src/d3d/gpu/threaded.cpp').read_text()
    k='else SendRange(now, r);'
    assert t.count(k)==1
    # Commands carry their offset and size. Copy changed contiguous ranges
    # once, instead of rescanning the enclosing range in 256/64-byte units.
    t='extern "C" unsigned whole_pick;\n'+t.replace(k,'else if (whole_pick) WriteDelta(r.off, now, r.len); '+k)
    p.add('threaded.cpp',t)
    src='unsigned whole_pick;\n#define cache_active whole_pick\n'+src
if '--collision' in sys.argv:
    p.link[next(i for i,v in enumerate(p.link) if v.endswith('/recomp_0026.o'))]=str(p.out/'collision-span.o')
    src='unsigned span_pick;\n#define cache_active span_pick\n'+src
if '--pair' in sys.argv or '--serial' in sys.argv:
    if '--serial' in sys.argv:src='static unsigned cache_active;\n'+src
    else:assert any(x in sys.argv for x in ('--cache','--collision','--whole','--tree'))
    src = src.replace('void __real_ngb_kernel_log',r"""
void angle_boundary(unsigned f, unsigned draws) {
    static unsigned previous_draws;
    static uint64_t previous_ns;
    struct timespec ts;
    if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&ts))abort();
    uint64_t now = (uint64_t)ts.tv_sec*1000000000u + ts.tv_nsec;
    if(f && previous_ns)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,cache_active,
              (unsigned long long)(now-previous_ns),draws-previous_draws);
    static uint64_t prev_ent,prev_poll;
    if(f)fprintf(stderr,"[OPEN_WORK] %u %llu %llu\n",f,(unsigned long long)(entries-prev_ent),(unsigned long long)(ngb_guest_polls-prev_poll));
    prev_ent=entries;prev_poll=ngb_guest_polls;
    previous_draws=draws;previous_ns=now;
    cache_active=(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));
}
void __real_ngb_kernel_log""",1)
    bridge = (RUNTIME/'scene/bridge.c').read_text()
    for anchor, frame in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
        assert bridge.count(anchor)==1
        bridge = bridge.replace(anchor,anchor+' extern void angle_boundary(unsigned,unsigned);angle_boundary('+frame+',draws);')
    if '--present-mix' in sys.argv:
        import runpy
        src=runpy.run_path(str(Path(__file__).with_name('present-mix.py')))['install'](p,RUNTIME,src)
        if '--paced-cumulative' in sys.argv:
            assert '--rng-correspondence' in sys.argv and '--draw-correspondence' not in sys.argv
            k='void angle_boundary(unsigned f, unsigned draws) {'
            assert src.count(k)==1
            src=src.replace(k,'#include <errno.h>\n'+Path(__file__).with_name('draw-cadence.inc').read_text()+k+' cadence_boundary(f);')
            p.link.insert(1,'-Wl,--wrap=ngb_poll_due')
        if '--title-device-prep' in sys.argv or '--title-worker-prep' in sys.argv:
            src=runpy.run_path(str(Path(__file__).with_name('title-device-prep.py')))['install'](p,src,'--title-worker-prep' in sys.argv)
        if '--rng-correspondence' in sys.argv:
            name='recomp_0037.c.o'
            old=[v for v in p.link if Path(v).name==name]; assert len(old)==1,old
            group='opening-rng-correspondence' if '--full-page' in sys.argv else 'opening-rng-original'
            p.link[p.link.index(old[0])]=str(p.core/group/name)
            anchor='void pm_present(unsigned draws,unsigned long long volume,unsigned long long sig){'
            assert src.count(anchor)==1
            src=src.replace(anchor,Path(__file__).with_name('rng-correspondence.inc').read_text()+anchor+' rr_present();')

    if '--draw-correspondence' in sys.argv:
        # Same HLE completion point as the Switch 0.55.0 DRAW_BOUND counter.
        h=(RUNTIME.parents[2]/'src/d3d/hle.cpp').read_text()
        hook='    if (measure) ngb_direct_draw_time'
        assert h.count(hook)==1
        if '--draw-cadence' in sys.argv:
            k='        if (g_backend) g_backend->Present(g_state.rt);'
            assert h.count(k)==1
            h=h.replace(k,'        if(g_backend) cadence_swap();\n'+k)
            h='extern "C" void cadence_swap(void);\n'+h
            src=src.replace('void angle_boundary(unsigned f, unsigned draws) {',
                '#include <errno.h>\n'+Path(__file__).with_name('draw-cadence.inc').read_text()+
                '\nstatic unsigned sw_total,sw_flips;extern unsigned correspondence_hle;\nvoid cadence_swap(void){++sw_total;}\nvoid angle_boundary(unsigned f,unsigned draws){cadence_boundary(f);if(f){fprintf(stderr,"[SWAP_SLICE] %u %u %u\\n",f,sw_total-sw_flips,correspondence_hle);}sw_flips=sw_total;')
            if '--draw-swap-budget' in sys.argv:
                src=src.replace('void cadence_swap(void){++sw_total;}',Path(__file__).with_name('draw-swap-budget.inc').read_text())
                src=src.replace('cadence_boundary(f);if(f)', 'sb_flip=f;cadence_boundary(f);if(f)')
            p.link.insert(1,'-Wl,--wrap=ngb_poll_due')
        p.add('hle.cpp','extern "C" unsigned correspondence_hle;\n'+h.replace(hook,'    ++correspondence_hle;\n'+hook))
        src='unsigned correspondence_hle;\n'+src
        hook='    previous_draws=draws;previous_ns=now;'
        assert src.count(hook)==1
        src=src.replace(hook,'    if(f){fprintf(stderr,"[DRAW_CORRESPOND] %u %u %u\\n",f,correspondence_hle,draws-previous_draws);}correspondence_hle=0;\n'+hook)
    if '--effective-mask' in sys.argv:
        k='ngb_poll_mask = 63;'
        assert bridge.count(k)==1
        bridge=bridge.replace(k,k+' extern void ngb_refresh_effective_mask(void); ngb_refresh_effective_mask();')
    if '--ticket' in sys.argv:
        k='ngb_poll_mask = 63;'
        assert bridge.count(k)==1
        bridge=bridge.replace(k,k+' extern uint64_t ticket_deadline; ticket_deadline=0;')
    if '--memory-census' in sys.argv:
        for f in ('0','scene_flips'):
            k=f'angle_boundary({f},draws);'
            assert bridge.count(k)==1
            bridge=bridge.replace(k,k+f' extern void census_flip(unsigned);census_flip({f});')
    if '--guard-host' in sys.argv:
        for f in ('0','scene_flips'):
            k=f'angle_boundary({f},draws);';assert bridge.count(k)==1
            bridge=bridge.replace(k,k+f' extern void guard_flip(unsigned);guard_flip({f});')
    if '--irq-cost' in sys.argv:
        for f in ('0','scene_flips'):
            k=f'angle_boundary({f},draws);'
            assert bridge.count(k)==1
            bridge=bridge.replace(k,k+f' extern void irq_window(unsigned);irq_window({f});')
    if '--model-nodes' in sys.argv:
        for f in ('0','scene_flips'):
            k=f'angle_boundary({f},draws);'
            assert bridge.count(k)==1
            bridge=bridge.replace(k,k+f' extern void node_flip(unsigned);node_flip({f});')
    if '--tree-update' in sys.argv:
        for f in ('0','scene_flips'):
            k=f'angle_boundary({f},draws);'
            assert bridge.count(k)==1
            bridge=bridge.replace(k,k+f' extern void task_flip(unsigned);task_flip({f});')
    if '--cb-cost' in sys.argv or '--task-cb' in sys.argv or '--task-edges' in sys.argv:
        for f in ('0','scene_flips'):
            k=f'angle_boundary({f},draws);'
            assert bridge.count(k)==1
            bridge=bridge.replace(k,k+f' extern void cb_flip(unsigned);cb_flip({f});')
    if {'--actor-phase','--product-reuse','--actor-kinds','--actor-time','--first-init','--word-site-census','--stack-window','--target-hist','--alloc-budget','--bulk-budget','--gate-pairs','--entry-stream','--fifo-groups','--pointer-sites','--scalar-slow','--lookup-mix','--index-origin','--header-sets','--pipeline-wait','--wait-origin','--clock-census','--tree-pair-cost','--tree-triple','--mixed-hit','--mixed-span','--axis-parent','--axis-query','--actor-tree','--actor-values','--actor-table','--light-budget','--light-path','--public-entry','--contact-budget','--matrix-budget','--row-bins','--row-reasons','--copy-coverage','--light-count','--audio-budget','--node-budget','--node-prefix','--family-budget','--node-family','--node-order','--node-census','--vm-block-census','--sync-budget','--delta-gap','--range-census','--snapshot-budget','--light-stages','--tree-census','--gate-census','--pointer-route','--cmd-budget','--cmd-pass','--box-budget','--box-scan','--box-reuse','--page-shape','--contact-repeat','--contact-blocks','--frame-pc','--poll-sample'} & set(sys.argv):
        for f in ('0','scene_flips'):
            k=f'angle_boundary({f},draws);'
            assert bridge.count(k)==1
            bridge=bridge.replace(k,k+f' extern void phase_flip(unsigned);phase_flip({f});')
    if '--span-audit' in sys.argv:
        for f in ('0','scene_flips'):
            k=f'angle_boundary({f},draws);'
            assert bridge.count(k)==1
            bridge=bridge.replace(k,k+f' extern void span_count_flip(unsigned);span_count_flip({f});')
    p.add('scene/bridge.c',bridge)
if '--draw-swap-budget' in sys.argv:
    assert src.count('}correspondence_hle=0;')==1
    src=src.replace('}correspondence_hle=0;', '}sb_hle_total+=correspondence_hle;correspondence_hle=0;')
if {'--retained-pgo-train','--retained-pgo-use','--retained-pgo-local','--partition-pgo'} & set(sys.argv):
    pg=p.core/('opening-partition-pgo' if '--partition-pgo' in sys.argv else 'opening-retained-pgo-local' if '--retained-pgo-local' in sys.argv else 'opening-retained-pgo')
    if '--no-tracer-partition' in sys.argv:
        assert '--partition-pgo' in sys.argv
        pg=p.core/'opening-partition-no-tracer'
    if '--no-unroll-partition' in sys.argv:
        assert '--partition-pgo' in sys.argv
        pg=p.core/'opening-partition-no-unroll'
    if '--early-sched-partition' in sys.argv:
        assert '--partition-pgo' in sys.argv
        pg=p.core/'opening-partition-early-sched'
    if '--align-hot-entry' in sys.argv:
        assert '--partition-pgo' in sys.argv
        pg=p.core/'opening-align-hot-entry'
    boundary='void angle_boundary(unsigned f, unsigned draws) {'
    clears=[]
    for u in (2,10,16,28,29):
        n=f'recomp_{u:04}.c.o';orig=p.core/('opening-compact-loops' if u in (2,10,16) else 'opening-full-page')/n
        p.link[p.link.index(str(orig))]=str(pg/n)
        clears.append(f'extern void clear_retained_{u}(void);clear_retained_{u}();')
    if '--retained-pgo-train' in sys.argv:
        assert src.count(boundary)==1
        src=src.replace(boundary,boundary+'if(!f){'+''.join(clears)+'}')
        import subprocess
        emitter=pg/'emit.o'
        subprocess.run(['cc','-O2','-c',Path(__file__).resolve().parents[2]/'perf/emit.c','-o',emitter],check=True)
        p.link.insert(1,str(emitter))
        p.link.append(str(pg/'gcov.a'))
if '--coord-control' in sys.argv or '--coord-xmm' in sys.argv:
    assert '--partition-pgo' in sys.argv
    obj='recomp_0028.c.o'
    variant='opening-coord-xmm' if '--coord-xmm' in sys.argv else 'opening-full-page'
    p.link[p.link.index(str(pg/obj))]=str(p.core/variant/obj)
if '--extra-partition' in sys.argv or '--extra-train' in sys.argv:
    assert '--partition-pgo' in sys.argv and '--retained-pgo-train' not in sys.argv
    pg=p.core/'opening-extra-partition'
    clears=[]
    for u in (0,1,9,15,26):
        n=f'recomp_{u:04}.c.o'
        orig=p.core/('opening-compact-loops' if u==26 else 'opening-full-page')/n
        p.link[p.link.index(str(orig))]=str(pg/n)
        clears.append(f'extern void clear_retained_{u}(void);clear_retained_{u}();')
    if '--extra-train' in sys.argv:
        boundary='void angle_boundary(unsigned f, unsigned draws) {'
        assert src.count(boundary)==1
        src=src.replace(boundary,boundary+'if(!f){'+''.join(clears)+'}')
        import subprocess
        emitter=pg/'emit.o'
        subprocess.run(['cc','-O2','-c',Path(__file__).resolve().parents[2]/'perf/emit.c','-o',emitter],check=True)
        p.link.insert(1,str(emitter));p.link.append(str(pg/'gcov.a'))
if '--target-library-pair' in sys.argv:
    # Bind six external calls in both arms straight to the target implementations, with no probe.
    assert not {'--target-trig','--target-memory'} & set(sys.argv)
    import subprocess
    for tag,names in [('memory',['memcmp','memcpy','memmove','memset']),('trig',['sin','cos'])]:
        target=p.out/('unmetered-'+tag+'.o')
        subprocess.run(['objcopy',*[arg for n in names for arg in ('--redefine-sym','ngb_dev_'+n+'=__wrap_'+n)],str(p.core/('opening-target-'+tag)/(tag+'.o')),str(target)],check=True)
        p.link[1:1]=['-Wl,'+','.join('--wrap='+n for n in names),str(target)]
if '--target-trig' in sys.argv:
    k='void angle_boundary(unsigned f, unsigned draws) {'
    assert src.count(k)==1
    src=src.replace(k,Path(__file__).with_name('target-trig.inc').read_text()+'\n'+k+'trig_boundary(f);')
    p.link[1:1]=['-Wl,--wrap=sin,--wrap=cos',str(p.core/'opening-target-trig/trig.o')]
if '--target-memory' in sys.argv:
    k='void angle_boundary(unsigned f, unsigned draws) {'
    assert src.count(k)==1
    src=src.replace(k,Path(__file__).with_name('target-memory.inc').read_text()+'\n'+k+'ms_boundary(f);')
    p.link[1:1]=['-no-pie','-Wl,--wrap=memcmp,--wrap=memcpy,--wrap=memmove,--wrap=memset',str(p.core/'opening-target-memory/memory.o')]
if '--seed-seven-old' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('seed-seven-unit.py')))['install'](p,REGS)
if '--merged-pgo' in sys.argv:
    for u in (2,16,28):
        name=f'recomp_{u:04}.c.o'
        p.link[p.link.index(str(REGS/name))]=str(p.core/'opening-merged-pgo'/name)
if '--reg-align-control' in sys.argv or '--reg-align-shift' in sys.argv:
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('xmm-align.py')))['install'](p,src,8 if '--reg-align-shift' in sys.argv else 0)
if '--dma-o2' in sys.argv:
    name='nv2a_boot.c'
    idx=[i for i,v in enumerate(p.link) if v.endswith('/'+name+'.o')]
    assert len(idx)==1 and p.link[idx[0]].startswith('CMakeFiles/')
    cc=[c for c in p.commands if c[-1].endswith('/'+name)]
    assert len(cc)==1 and cc[0].count('-O1')==1
    cc[0][cc[0].index('-O1'):cc[0].index('-O1')+1]=['-O2','-fno-strict-aliasing']
    p.link[idx[0]]=p.compile(name,(RUNTIME/name).read_text())
if '--dma-reject-mix' in sys.argv:
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('dma-reject-mix.py')))['install'](p,RUNTIME,src)
if '--dma-state-families' in sys.argv:
    import runpy
    name='nv2a_boot.c'
    idx=[i for i,v in enumerate(p.link) if v.endswith('/'+name+'.o')]
    assert len(idx)==1 and p.link[idx[0]].startswith('CMakeFiles/')
    p.link[idx[0]]=p.compile(name,runpy.run_path(str(Path(__file__).with_name('dma-state-families.py')))['transform']((RUNTIME/name).read_text()))
if '--arch-clock' in sys.argv:
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('arch-clock.py')))['install'](p,src)
if '--runtime-core-o2' in sys.argv:
    k='#include "host-runtime.inc"'
    assert src.count(k)==1 and '--partition-pgo' in sys.argv
    src=src.replace(k,'#pragma GCC push_options\n#pragma GCC optimize ("O2","no-strict-aliasing")\n'+k+'\n#pragma GCC pop_options')
if '--xdk-body-ledger' in sys.argv:
    anchor='void angle_boundary(unsigned f, unsigned draws) {'
    assert src.count(anchor)==1 and '--after-regs' in sys.argv
    src=src.replace(anchor,Path(__file__).with_name('xdk-body-ledger.inc').read_text()+'\n'+anchor+' xbl_boundary(f);')
if '--before-ledger' in sys.argv:
    anchor='void angle_boundary(unsigned f, unsigned draws) {'
    assert src.count(anchor)==1 and '--after-regs' in sys.argv
    src=src.replace(anchor,Path(__file__).with_name('before-ledger.inc').read_text()+'\n'+anchor+' bl_boundary(f);')
if '--select-budget' in sys.argv:
    anchor='void angle_boundary(unsigned f, unsigned draws) {'
    assert src.count(anchor)==1 and '--after-regs' in sys.argv
    src=src.replace(anchor,Path(__file__).with_name('select-budget.inc').read_text()+'\n'+anchor+' sel_boundary(f);')
if '--vm-access-budget' in sys.argv:
    anchor='void angle_boundary(unsigned f, unsigned draws) {'
    assert src.count(anchor)==1
    src=src.replace(anchor,Path(__file__).with_name('vm-access-budget.inc').read_text()+'\n'+anchor+' vb_boundary(f);')
    p.link.insert(1,'-Wl,--wrap=ngb_vm_access')
if '--dma-coverage' in sys.argv:
    assert '--partition-pgo' in sys.argv and '--rng-correspondence' in sys.argv
    name='nv2a_boot.c'
    idx=[i for i,v in enumerate(p.link) if v.endswith('/'+name+'.o')]
    assert len(idx)==1 and p.link[idx[0]].startswith('CMakeFiles/')
    p.link[idx[0]]=p.compile(name,(RUNTIME/name).read_text(),['-fprofile-arcs','-ftest-coverage','-fprofile-update=atomic'])
    anchor='void angle_boundary(unsigned f, unsigned draws) {'
    assert src.count(anchor)==1
    src=src.replace(anchor,'extern void __gcov_reset(void), __gcov_dump(void);\n'+anchor+' if(f==30)__gcov_reset(); if(f==120)__gcov_dump();')
    p.link.append('-lgcov')
if {'--hle-pgo-train','--hle-pgo-use'} & set(sys.argv):
    assert '--present-mix' in sys.argv and '--partition-pgo' in sys.argv
    train='--hle-pgo-train' in sys.argv
    directory=p.out.parent/'hle-counters'
    directory.mkdir(exist_ok=True)
    # Keep the exact candidate HLE, Present diagnostics, header paths and object name.
    assert str(p.out/'hle.cpp.o') in p.link
    opts=['-fprofile-generate='+str(directory),'-fprofile-update=atomic'] if train else ['-fprofile-use='+str(directory),'-Werror=missing-profile','-Werror=coverage-mismatch','-fprofile-partial-training','-fno-profile-values']
    p.compile('hle.cpp',(p.out/'hle.cpp').read_text(),opts)
    if train:
        anchor='void angle_boundary(unsigned f, unsigned draws) {'
        assert src.count(anchor)==1
        src=src.replace(anchor,'extern void __gcov_reset(void), __gcov_dump(void);\n'+anchor+' if(!f)__gcov_reset(); if(f==120)__gcov_dump();')
        p.link.append('-lgcov')
if '--buffer-frame-log' in sys.argv:
    import runpy
    src=runpy.run_path(str(Path(__file__).with_name('buffer-frame-log.py')))['transform'](src)
if '--stack-pair-count' in sys.argv:
    import runpy
    stk=runpy.run_path(str(Path(__file__).with_name('stack-pair-counter.py')))
    src=stk['driver'](src)
obj = p.compile('runtime_test.c',src,[*(['-D_GNU_SOURCE=1'] if '--frame-pc' in sys.argv else []),'-I'+str(REGS),'-I'+str(RUNTIME),'-include',str(RUNTIME/'switch_guest_regs.h'),'-DNGB_REGISTER_PACKAGE','-DNGB_RIGID_CLIP'])
p.link[p.link.index(str(p.core/'exact-runtime_test.c.o'))] = obj
for name in ('identity','scanout','files','opening_movie'):
    p.link[p.link.index('CMakeFiles/ngb-runtime-test.dir/'+name+'.c.o')] = str(p.out/(name+'.c.o'))
ohci_src=(RUNTIME/'ohci_boot.c').read_text()
if '--ohci-tick-limit' in sys.argv:
    assert '--arch-clock' in sys.argv
    k='uint64_t now = ngb_elapsed_ns(), frames = (now - frame_epoch) / 1000000;'
    assert ohci_src.count(k)==1
    ohci_src=ohci_src.replace(k,'extern uint64_t opening_ohci_frames(uint64_t); uint64_t frames=opening_ohci_frames(frame_epoch);')
pad=p.compile('ohci_boot.c',ohci_src)
p.link[next(i for i,v in enumerate(p.link) if v.endswith('/ohci_boot.c.o'))]=pad
p.link.insert(1,'-Wl,--wrap=ngb_scanout_direct,--strip-debug')
if '--lookup-front' in sys.argv:
    import runpy
    runpy.run_path(str(Path(__file__).with_name('lookup-front.py')))['install'](p)
if '--entry-literal' in sys.argv:
    import runpy
    literals=runpy.run_path(str(Path(__file__).with_name('entry-literal.py')))
    literals['install'](p,REGS)
if '--gate-sites' in sys.argv:
    import runpy
    gs=runpy.run_path(str(Path(__file__).with_name('gate-sites.py')))
    gate_sites=gs['install'](p)
if '--alias-host' in sys.argv:
    import subprocess
    obj=p.out/'alias-host.o'
    source=Path(__file__).with_name('alias-host.c')
    if '--guard-host' in sys.argv:
        source=p.out/'guard-host.c';source.write_text(runpy.run_path(str(Path(__file__).with_name('guard-view.py')))['allocator']())
    subprocess.run(['cc','-O2','-c',source,'-o',obj],check=True)
    p.link[1:1]=['-Wl,--wrap=calloc,--wrap=free',str(obj)]
if '--stack-inner-span' in sys.argv:
    ix,=[i for i,v in enumerate(p.link) if v.endswith('/recomp_0033.c.o')]
    p.link[ix]=str(p.core/'opening-stack-inner-span/recomp_0033.c.o')
p.finish()
if '--stack-pair-count' in sys.argv:stk['patch'](p.out/'replay')
if '--gate-sites' in sys.argv:gs['patch'](p.out/'replay',gate_sites)
if '--entry-literal' in sys.argv:literals['patch'](p.out/'replay')

if {'--entry-chains','--stream-layout','--pc-density','--hot-layout'} & set(sys.argv):
    import subprocess, re
    elf=p.out/'replay'
    hdr=subprocess.check_output(['objdump','-h',elf],text=True)
    m=re.search(r'^\s*\d+\s+\.text.ngb_opening\s+([0-9a-f]+)\s+([0-9a-f]+)',hdr,re.M)
    assert m,'linker did not create opening section'
    size,first=map(lambda v:int(v,16),m.groups())
    syms=subprocess.check_output(['nm','-n',elf],text=True)
    actual={n:int(pc,16) for pc,n in re.findall(r'^([0-9a-f]+) [tT] ngb_reg_(sub_[A-F0-9]+)$',syms,re.M)}
    order=re.findall(r'\(\.text\.(sub_[0-9A-F]+)\)',ld.read_text())
    offsets=[actual[n] for n in order]
    assert offsets==sorted(set(offsets)) and first<=offsets[0]<=offsets[-1]<first+size
    if '--entry-chains' in sys.argv: runpy.run_path(str(Path(__file__).with_name('entry-chains.py')))['verify'](REGS.parent,elf)
    if '--stream-layout' in sys.argv:
        for cluster in ld.read_text().split('. = ALIGN(4096);')[1:]:
            pages={actual[n]//4096 for n in re.findall(r'\(\.text\.(sub_[0-9A-F]+)\)',cluster)}
            assert len(pages)==1, pages
    print('verified linked opening layout',len(order),'functions',size,'bytes',flush=True)
