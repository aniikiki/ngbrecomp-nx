"""Compare real runtime checkpoint code and generated entry macro through
startup, ticket wrap and a due service mutating counters / history."""
from pathlib import Path
import runpy,subprocess,tempfile
p=Path(__file__).resolve().parent
pre=runpy.run_path(str(p/'hot-entry.py'))['pre']
s=(p.parents[1]/'runtime/runtime.c').read_text()
fn=s[s.index('void ngb_checkpoint(uint32_t va)\n{'):s.index('void ngb_poll_due(uint64_t ticket)\n{')]
c='''
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#define recent ngb_reg_recent
#define current_va ngb_reg_current_va
#define entries ngb_reg_entries
uint32_t current_va,recent[32],mask,pending,events,due;
uint64_t entries,tickets,checksum;
static void checkpoint_event(uint32_t v){events++;checksum+=v+entries;}
static void ngb_guest_block_poll(void){tickets++;if(!(tickets&mask)||pending){
 ++due;checksum=checksum*33+current_va+recent[(entries-1)&31];pending=0;
 if(!(due%7)){recent[entries++&31]=current_va+4;current_va+=4;} }}
'''+fn+pre+'''
struct snap {uint32_t va,r[32],pending_,events_,due_;uint64_t e,t,c;};
static void run(unsigned test,unsigned init,unsigned m,unsigned pend,struct snap*out){
 memset(recent,0,sizeof recent);entries=init;tickets=UINT64_MAX-31;mask=m;pending=pend;current_va=due=events=0;checksum=0;
 for(unsigned i=0;i<513;i++){
#define VISIT(a) do{if(test)HOT_ENTRY(a);else ngb_checkpoint(a);}while(0)
 switch(i%59){case 0:VISIT(0x17a010u);break;case 1:VISIT(0x31dc50u);break;case 2:VISIT(0x3cc310u);break;default:VISIT(0x140af0u);break;}
 struct snap*v=&out[i];v->va=current_va;memcpy(v->r,recent,sizeof recent);v->pending_=pending;v->events_=events;v->due_=due;v->e=entries;v->t=tickets;v->c=checksum;
 }}
int main(){static struct snap a[513],b[513];unsigned n=0;for(unsigned i=0;i<65;i++)for(unsigned m=1;m<256;m=m*2+1)for(unsigned pend=0;pend<2;pend++){
 run(0,i,m,pend,a);run(1,i,m,pend,b);assert(!memcmp(a,b,sizeof a));n+=513;}printf("%u matching entry transitions\\n",n);}
'''
with tempfile.TemporaryDirectory() as td:
 f=Path(td)/'check.c';e=f.with_suffix('');f.write_text(c)
 subprocess.run(['cc','-O2',f,'-o',e],check=True);subprocess.run([e],check=True)
