"""Start native ARM actors speculatively BEFORE their parent supplies any
per-actor state. Derive only the original loop's incoming scalar arguments
from its immutable actor list. Check every observable write and register
against serial execution. Diagnostic only: no speculation is committed."""
from pathlib import Path
import subprocess as sp,sys
s=sp.check_output([sys.executable,Path(__file__).with_name('worker-snapshot.py')],text=True)
s=s.replace('num=0;result->ok=0;result->func_n=0;','num=0;')
s=s.replace('result=mmap(0,sizeof(*result)', 'result=mmap(0,64*sizeof(*result)')
a=s.index('     close(pipes_[j][1]);');b=s.index('     return;',a)
s=s[:a]+'''     close(pipes_[j][1]);close(pipes_[j][0]);actor_fork_child=1;alarm(3);slot=j;result+=slot;
     struct context*c=input+j;unsigned nr=fork_regs(c->regs,&c->entries);
     uint32_t *r=(uint32_t*)c->regs;unsigned char actor_id=base[sp+24+j];if(actor_id>=64||r[4]<=j)_exit(93);
     uint32_t obj=0x4b4e50+0x2800u*actor_id;
     if(j){base[sp+20]=actor_id;r[4]-=j;r[6]=obj;
      r[0]=fork_word(obj+0x26d8);r[1]=0;
      if(r[0]){r[2]=fork_word(r[0]+24);r[0]=fork_word(r[0]+r[2]);
       if(r[0]){r[1]=fork_word(r[0]+4);if(r[1]){r[1]=fork_word(r[0]+r[1]);if(r[1])r[1]+=r[0];}}}
     }else if(actor_id!=id)_exit(94);
     fork_restore(c->regs,p0,e0);
     id=actor_id;initial_sp=sp;dep_task=TAG|256|id;child=0;
'''+s[b:]
s=s.replace('extern void fork_restore','extern unsigned fork_word(unsigned);extern void fork_restore').replace('   for(unsigned j=0;j<11;j++){','   for(unsigned j=0;j<11;j++){result[j].ok=0;result[j].func_n=0;')
a=s.index('  struct context*c=input+slot;fork_regs');b=s.index('\n }',a)
s=s[:a]+'''  child=pids[slot];close(pipes_[slot][1]);result+=slot;
'''+s[b:]
s=s.replace('num=0;result->ok=0;','num=0;').replace('seen[written[j]]=0;scope=0;','seen[written[j]]=0;scope=0;result-=slot;').replace('[NATIVE_SNAPSHOT]','[NATIVE_AHEAD]')
print(s)
