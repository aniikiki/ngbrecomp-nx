"""Drive the retail New Game path after widescreen movie teardown, then confirm movie scanouts."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import NativeProbe,REGS,RUNTIME
p=NativeProbe('wide-start')
s=(REGS/'host-driver.c').read_text()
s=s.replace('void __real_ngb_kernel_log','static uint64_t intro_done;\nvoid __real_ngb_kernel_log',1)
s=s.replace('    __real_ngb_kernel_log(message);','    if(strstr(message,"Opening movie EOF"))intro_done=ngb_elapsed_ns()/1000000;\n    __real_ngb_kernel_log(message);')
s=s.replace('if (frame_signature(pixels,103,621,11,142,341,13) != 0xa0a5912du) return;', 'if (!intro_done || now<intro_done+5000) return;')
s=s.replace('if (menu_cursor != 0 || frame_signature(pixels,190,535,8,36,70,5) != 0x86badb68u) return;', 'if (menu_cursor != 0) return;')
s=s.replace('    __real_ngb_kernel_log(message);','    __real_ngb_kernel_log(message);\n    if(strstr(message,"Movie content changes=30"))ngb_stop("verified moving New Game movie",30);')
if '--chapter' in sys.argv:
 s=s.replace('static uint64_t intro_done;', 'static uint64_t intro_done;static unsigned chapter,chapter_frames,chapter_changes;')
 s=s.replace('    __real_ngb_kernel_log(message);','    if(strstr(message,"native chapter CG"))chapter=1;\n    __real_ngb_kernel_log(message);',1)
 s=s.replace('    previous=hash;', '    if(chapter){chapter_changes+=hash!=previous; if(++chapter_frames%60==0)fprintf(stderr,"[CG_CHECK] frames=%u changes=%u\\n",chapter_frames,chapter_changes); if(chapter_frames>=150 && chapter_changes>=30){ ngb_ohci_pad_sample(16,0,0,0,0);} }\n    previous=hash;')
 s=s.replace('if(strstr(message,"Movie content changes=30"))','if(chapter && strstr(message,"Opening movie skipped") && chapter_frames>=150)')
 s=s.replace('verified moving New Game movie','verified native CG motion and Start skip')
o=p.compile('runtime_test.c',s,['-I'+str(REGS),'-I'+str(RUNTIME),'-include',str(RUNTIME/'switch_guest_regs.h'),'-DNGB_REGISTER_PACKAGE','-DNGB_RIGID_CLIP'])
p.link[p.link.index(str(p.core/'exact-runtime_test.c.o'))]=o
for name in ('identity','scanout','files','opening_movie'):
 p.link[p.link.index('CMakeFiles/ngb-runtime-test.dir/'+name+'.c.o')]=str(p.out/(name+'.c.o'))
if '--chapter' in sys.argv:
 for name in ('files','opening_movie','ohci_boot'):
    q=p.compile(name+'.c',(RUNTIME/(name+'.c')).read_text())
    if name=='ohci_boot':p.link[next(i for i,v in enumerate(p.link) if v.endswith('/ohci_boot.c.o'))]=q
 (p.out/'inline_draw.inc').write_text((RUNTIME/'inline_draw.inc').read_text())
if '--measure' in sys.argv:
    inc=(RUNTIME/'inline_draw.inc').read_text().replace('    if (b[0]==a[0]',r"""
    static unsigned calls; static uint64_t raster_ns;
    uint64_t start=ngb_elapsed_ns();
    if(calls<2 || calls==80)fprintf(stderr,"[RECT] %g %g -> %g %g UV %g %g -> %g %g filter=%08x\n",a[0],a[1],b[0],c[1],a[4],a[5],b[4],c[5],m[NV097_SET_TEXTURE_FILTER/4]);
    if (b[0]==a[0]""").replace('    /* Log a few content',r"""
    raster_ns+=ngb_elapsed_ns()-start;
    if(++calls%30==0)fprintf(stderr,"[RASTER] %u %.3f ms/draw\n",calls,(double)raster_ns/calls/1e6);
    /* Log a few content""")
    (p.out/'inline_draw.inc').write_text(inc)
    mov=(RUNTIME/'opening_movie.c').read_text().replace('selected_wide = !strcasecmp','fprintf(stderr,"[SELECT] %s\\n",name);selected_wide = !strcasecmp')
    mo=p.compile('opening_movie.c',mov)
    p.link[p.link.index(str(p.out/'opening_movie.c.o'))]=mo
q=p.compile('pgraph_boot.c',(RUNTIME/'pgraph_boot.c').read_text())
i=next(i for i,v in enumerate(p.link) if v.endswith('/pgraph_boot.c.o'));p.link[i]=q
p.link.insert(1,'-Wl,--strip-debug');p.finish()
