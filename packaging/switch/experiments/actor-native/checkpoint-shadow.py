"""Compare each true parent due-interrupt boundary with the isolated worker.
Remove tickets accumulated by other fibers or hardware callbacks."""
from pathlib import Path
import subprocess as sp,sys
s=sp.check_output([sys.executable,Path(__file__).with_name('shadow.py')],text=True)
s=s.replace('uint64_t*,uint64_t*);','uint64_t*,uint64_t*,uint8_t*,unsigned,unsigned*);',1)
s=s.replace('static pthread_t worker;', '''static pthread_t worker;static unsigned events,ndue,counting;
static uint8_t trace[8192][520],due_regs[8192][512];static unsigned at[8192];
static uint64_t charged,start_p;
void actor_due(void){if(!counting)return;if(ndue==8192)abort();uint64_t n;
 at[ndue]=charged+ngb_guest_polls-start_p;fork_regs(due_regs[ndue++],&n);}
''')
s='\n#include <stdint.h>\nextern uint64_t ngb_guest_polls;extern unsigned fork_regs(void*,uint64_t*);\n'+s
s=s.replace('pages,&ticks,&ent);','pages,&ticks,&ent,&trace[0][0],520,&events);')
s=s.replace('void dep_key(unsigned k){active=', 'void dep_key(unsigned k){if(counting){charged+=ngb_guest_polls-start_p;counting=0;}active=').replace('stage=k>>8&1;id=k&63;}}','stage=k>>8&1;id=k&63;}if(scope&&active&&stage){counting=1;start_p=ngb_guest_polls;}}')
s=s.replace('ticks=p0=ngb_guest_polls;ent=0;', 'ticks=p0=ngb_guest_polls;ent=0;charged=ndue=events=0;start_p=p0;counting=1;')
s=s.replace('  unsigned diff=0,extra=0', '''  unsigned boundary_err=0;for(unsigned q=0;q<ndue;q++){
   unsigned t=at[q];if(!t||t>events||memcmp(trace[t],due_regs[q],nr)){
    if(++boundary_err==1){unsigned a=0;while(t<=events&&a<nr&&trace[t][a]==due_regs[q][a])a++;
     fprintf(stderr,"[IRQ_DIFF] actor=%u ticket=%u max=%u offset=%u\\n",id,t,events,a);}}}
  fprintf(stderr,"[IRQ_COMPARE] actor=%u boundaries=%u bad=%u\\n",id,ndue,boundary_err);counting=0;
  unsigned diff=0,extra=0''')
print(s)
