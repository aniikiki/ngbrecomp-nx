"""Spawn suspended native ARM copies at the FIRST actor of each selected frame.
Supply only register/stack inputs and scheduler counters from each actor entry.
All heap, model, world/collision state stays at the first-actor version."""
from pathlib import Path
s=Path(__file__).with_name('actor-fork.c').read_text()
s=s.replace('static pid_t child;', '''static pid_t child,pids[64];static int pipes_[64][2];static unsigned iter,slot;
static struct context {uint8_t regs[512];uint64_t polls,entries;unsigned sp,id,parent;uint8_t stack[16384+256];} *input;
extern void fork_restore(const void*,uint64_t,uint64_t);''')
s=s.replace('result=mmap', '''input=mmap(0,64*sizeof(*input),PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);if(input==MAP_FAILED)abort();
 result=mmap''')
a=s.index('  child=fork();');b=s.index('\n }',a)
s=s[:a]+'''
  if(!iter){
   // Slots used in both captured windows are known; extra slots are never
   // assumed safe. At the frame boundary explicitly cancel unused replicas.
   for(unsigned j=0;j<11;j++){
    if(pipe(pipes_[j]))abort();pid_t pid=fork();if(pid<0)abort();
    if(!pid){
     close(pipes_[j][1]);char ch;alarm(10);
     if(read(pipes_[j][0],&ch,1)!=1||ch!='r')_exit(0);
     actor_fork_child=1;alarm(2);slot=j;struct context*c=input+j;
     fork_restore(c->regs,c->polls,c->entries);p0=c->polls;e0=c->entries;
     memcpy(base+c->sp-16384,c->stack,sizeof c->stack);
     id=c->id;sp=c->sp;initial_sp=sp;prior[1][id]=c->parent;dep_task=TAG|256|id;child=0;
     return;
    }pids[j]=pid;close(pipes_[j][0]);
   }
  }
  slot=iter++;
  if(slot>=11){scope=0;return;}
  struct context*c=input+slot;fork_regs(c->regs,&c->entries);c->polls=ngb_guest_polls;c->id=id;c->sp=sp;c->parent=prior[1][id];
  if(sp<16384||sp+256>RAM)abort();memcpy(c->stack,base+sp-16384,sizeof c->stack);
  child=pids[slot];if(write(pipes_[slot][1],"r",1)!=1)abort();close(pipes_[slot][1]);
'''+s[b:]
s=s.replace('if(s && (frame==1802||frame==1808))','if(s && ((i==0 && (frame==1802||frame==1808) && !iter) || (iter && iter<11)))')
s=s.replace('if(active&&scope)abort();frame=', '''if(active&&scope)abort();
 if(iter==11 && !scope)iter=0;
 frame=''').replace('[NATIVE_ACTOR]','[NATIVE_SNAPSHOT]')
print(s)
