"""Measure the historical device-selected 1D9610 subtree during a wide replay.
Reuse the fiber-aware exclusive clock and ARM event wrappers from part-budget."""
from pathlib import Path
def install(p,regs,runtime,src):
    script=Path(__file__).with_name('part-budget.py').read_text()
    a=script.index("s=(REGS/'recomp_0028.c.gated.s')")
    b=script.index("(p.out/'host-runtime.inc').write_text",a)
    obj=regs/'recomp_0016.c.o'
    scope=script[a:b].replace('recomp_0028','recomp_0016').replace('003078B0','001D9610').replace("['001D9610','0030BCA0']","['001D9610']")
    ctx={'REGS':regs,'RUNTIME':runtime,'p':p}
    import re,subprocess as sp
    ctx['re']=re
    exec(scope,ctx)
    hooks=script.split("p.driver('static const unsigned owner[]=",1)[1].split("s+='",1)[0]
    hooks=eval("'static const unsigned owner[]="+hooks.strip()[:-1],ctx).replace('[PART_BUDGET]','[TREE_UPDATE]')
    code=ctx['s']+'\n.text\n'+ctx['wr']
    f=p.out/'tree-update.s';o=f.with_suffix('.o');f.write_text(code)
    sp.run(['cc','-c',f,'-o',o],check=True);f.unlink()
    p.link[p.link.index(str(obj))]=str(o)
    (p.out/'tree-sites.txt').write_text('\n'.join(f'{i} {row}' for i,row in enumerate(ctx['sites'],1))+'\n')
    return src.replace('void __real_ngb_kernel_log',hooks+'\nvoid __real_ngb_kernel_log',1)
