"""Link the port's hand-written gameplay functions into the retained ARM build.

Guest callers keep Xbox registers in x19..25. Desktop-style C handlers use
the same register file as the ordinary ABI gates; synchronize at the boundary.
Only change copies of objects in the temporary link directory.
"""
import re, shlex, subprocess as sp
from pathlib import Path
SRC=Path('/work/src')
ROOT=Path('/work/packaging/switch/runtime')
def technique_icons(unit):
    a=unit.index('void sub_001EAA10(void)\n{')
    body=unit[a:unit.index('\n}',a)+2]
    old='loc_001EADC8: ;\n    if (_flags /* js: sign (negative) */)'
    if old in body:body=body.replace(old,'loc_001EADC8: ;\n    if (_fas < 0)')
    assert '_fas < 0' in body.split('loc_001EADC8: ;',1)[1].split('goto',1)[0]
    return body

def mission_loop(unit):
    a=unit.index('void sub_00175A00(void)\n{')
    body=unit[a:unit.index('\n}',a)+2]
    # Retail Mission selection owns this loop until return, including
    # the difficulty overlay. The original three callees stay intact.
    for addr,probe in [('14','ngb_mission_stage(0,MEM32(edi+8))'),
                       ('1B','ngb_mission_stage(1,0)'),('20','ngb_mission_stage(2,0)'),
                       ('42','ngb_mission_stage(3,0)'),('44','ngb_mission_dump()')]:
        tag='loc_00175A'+addr+': ;'
        assert body.count(tag)==1
        body=body.replace(tag,tag+' if(ngb_mission_enabled) '+probe+';')
    return '#define RECOMP_GENERATED_CODE\n#include "recomp_funcs.h"\n#define NGB_MISSION_PROBE 1\n#include "mission_perf.h"\n'+body

def install(commands,b,d,link,regs):
    base=next(shlex.split(c) for c in commands if c.endswith('/runtime.c'))
    tool=Path(base[0]).parent
    def compile(name,body,flags=()):
        p=d/name;p.write_text(body);o=p.with_suffix('.o')
        c=base.copy();c[-1]=str(p);c[c.index('-o')+1]=str(o);c[c.index('-MF')+1]=str(o)+'.d'
        c[1:1]=['-I'+str(ROOT),'-I/work/src','-I/work/xboxrecomp/src/kernel','-include',str(ROOT/'switch_guest_regs.h'),'-ffunction-sections','-fdata-sections',*flags]
        if name.endswith('.S'): c=[base[0],'-c',str(p),'-o',str(o)]
        sp.run(c,cwd=b,check=True);link.insert(1,str(o))
    funcs=[]
    for name in ('hud','camera','cheats','ut_charge','responsive','intercept','cutscene_skip','quick_select','quick_ui','costume_menu','talisman','missions','mission_loop','technique_icons','pause_tabs','load_detail'):
        if name=='load_detail':
            # Same GPU cycle delta as the lifted rdtsc/sub/sbb callback.
            s="""#define RECOMP_GENERATED_CODE
#include "recomp_funcs.h"
int ngb_pc_setting(int);
void sub_0030E060(void)
{
    uint64_t ticks=0;
    if(ngb_pc_setting(29))ticks=xbox_ReadTimeStampCounter()-((uint64_t)MEM32(0xD21684)<<32|MEM32(0xD21680));
    MEM32(0xD21690)=eax=(uint32_t)ticks;MEM32(0xD21694)=edx=(uint32_t)(ticks>>32);esp+=4;
}
"""
        elif name=='mission_loop':
            s=mission_loop((SRC.parent/'build/switch-runtime/gen/recomp_0012.c').read_text())
        elif name=='missions':
            tail=(SRC/'main_menu.c').read_text().split('static uint8_t mission_bits(',1)[1]
            s='#define RECOMP_GENERATED_CODE\n#include "recomp_funcs.h"\nstatic uint8_t mission_bits('+tail
        elif name=='pause_tabs':
            # Mark the retail pause page at its own draw call. Other menus
            # can leave both the pause-state byte and the Exit index stale.
            unit=(SRC.parent/'build/switch-runtime/gen/recomp_0013.c').read_text()
            a=unit.index('void sub_00182240(void)\n{')
            body=unit[a:unit.index('\n}',a)+2]
            tag='RECOMP_ENTRY(0x00182240u);'
            assert body.count(tag)==1
            body=body.replace(tag,tag+'\n    if(MEM32(esp)==0x00180CC9u) ngb_pause_tab_seen(MEM8(0xDA41D1));')
            s='#define RECOMP_GENERATED_CODE\n#include "recomp_funcs.h"\nvoid ngb_pause_tab_seen(unsigned);\n'+body
        elif name=='technique_icons':
            unit=(SRC.parent/'build/switch-runtime/gen/recomp_0018.c').read_text()
            body=technique_icons(unit)
            s='#define RECOMP_GENERATED_CODE\n#include "recomp_funcs.h"\n'+body
        elif name=='talisman':s=(ROOT.parent/'settings/talisman.c').read_text()
        else:s=(SRC/(name+'.c')).read_text()
        if name=='costume_menu':
            s=s.replace('#include "xbox_memory_layout.h"','extern uint32_t xbox_HeapAlloc(uint32_t,uint32_t);')
            s='#define NGB_SWITCH_COSTUME_PICTURES 1\n'+s.replace('        ngb_sprite_range_dump();','        (void)0;')
        if name=='cheats':
            s=s.replace('#include "xbox_memory_layout.h"','')
            a=s.index('void ngb_frame_tick(void)');b1=s.index('/* ---- every difficulty',a)
            s=s[:a]+'''void ngb_switch_cheat_tick(void){cheat_tick();}\n'''+s[b1:]
        if name=='quick_ui':
            a=s.index('static void test_input(void)');z=s.index('    SDL_AtomicLock(&s_lock);',s.index('void ngb_quick_poll(void)',a))
            s=s[:a]+'void ngb_switch_quick_pad(unsigned bits) {\n'+s[z:]
            s=s.replace('FILE *f = xbox_mod_file(archive, path, sizeof path) ? fopen(path, "rb") : NULL;', 'FILE *f = NULL;')
        # As in the player runtime, keep debug traces off the hot path.
        s='#include "player_diagnostics.h"\n#define SETTINGS_TRACE(...) do { if(NGB_DIAG) fprintf(stderr,__VA_ARGS__); } while(0)\n'+s.replace('fprintf(stderr,','SETTINGS_TRACE(')
        defs=re.findall(r'^void (sub_[0-9A-F]+)\(void\)\n\{',s,re.M)
        for fn in defs:s=s.replace('void '+fn+'(void)\n{','void ngbs_'+fn+'(void)\n{')
        funcs+=defs
        compile(name+'.c',s,['-I/opt/devkitpro/portlibs/switch/include/SDL2','-Wno-unused-variable','-Wno-unused-function','-Wno-unused-label','-Wno-unused-but-set-variable','-Wno-int-conversion','-Wno-missing-field-initializers','-Wno-misleading-indentation'])
    lib='/opt/devkitpro/portlibs/switch/lib/libSDL2.a'
    # Only upstream timer/spinlock routines are needed.
    link.insert(link.index('-lnx'),lib)
    store='stp w19,w20,[x28]\nstp w21,w22,[x28,8]\nstp w23,w24,[x28,16]\nstr w25,[x28,24]'
    asm='.text\n'
    for f in funcs:
        # Preserve the existing optimized ARM body on the daily path.
        off=('adrp x9,ngb_mission_enabled\nldr w9,[x9,:lo12:ngb_mission_enabled]\ncbnz w9,1f\nb ngb_mission_original\n1:\n'
             if f=='sub_00175A00' else '')
        asm+=f'.global ngb_reg_{f}\n.type ngb_reg_{f},%function\nngb_reg_{f}:\n{off}stp x29,x30,[sp,-16]!\n{store}\nbl ngbs_{f}\n'+store.replace('stp','ldp').replace('str','ldr')+f'\nldp x29,x30,[sp],16\nret\n.size ngb_reg_{f},.-ngb_reg_{f}\n'
    compile('gameplay.S',asm)
    names=set('ngb_reg_'+f for f in funcs)
    found=set()
    nm=sp.check_output([tool/'aarch64-none-elf-nm','-A','-g','--defined-only',*regs],text=True)
    for obj in regs:
        subset={line.split()[-1] for line in nm.splitlines() if line.startswith(str(obj)+':')}&names
        if subset:
            dest=d/('retained-'+obj.name)
            alias=[]
            if 'ngb_reg_sub_00175A00' in subset:
                table=sp.check_output([tool/'aarch64-none-elf-objdump','-t',obj],text=True)
                orig=next(l.split() for l in table.splitlines() if l.endswith(' ngb_reg_sub_00175A00'))
                alias=['--add-symbol',f'ngb_mission_original={orig[3]}:0x{orig[0]},global,function']
            sp.run([tool/'aarch64-none-elf-objcopy',*alias,*['--weaken-symbol='+n for n in sorted(subset)],obj,dest],check=True)
            link[link.index(str(obj))]=str(dest);found.update(subset)
    assert found==names,names-found
