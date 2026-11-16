"""Record worker architectural state at every private poll for differential
comparison with the original game at due interrupts. Offline object only."""
from pathlib import Path
here=Path(__file__).resolve().parent
s=(here/'build.py').read_text().replace("d=p/'opt050/actor-native'","d=p/'opt050/actor-checkpoints'")
# Some original native helpers retire several polls at once. A replay
# that needs every intermediate state must take their original scalar path.
s=s.replace(' srcs[va]=src\ncode+=', " src=src.replace('#include \"scan_tags.inc\"','/* expand polls in the ordinary scalar loop */')\n srcs[va]=src\ncode+=")
s=s.replace('#define ngb_pending_dpcs 0u','#define ngb_pending_dpcs 1u')
s=s.replace(' unsigned pc,error;', ' unsigned char* trace;unsigned stride,events;unsigned pc,error;')
s=s.replace('static inline void ngb_guest_block_poll(void){++ac.polls;}','''static inline void ngb_guest_block_poll(void){
 ++ac.polls;if(++ac.events>=8192){ac.error=~0u;longjmp(ac.unwind.escape,1);}
 unsigned char *dst=ac.trace+(size_t)ac.events*ac.stride;__builtin_memcpy(dst,&ac.regs,sizeof(ac.regs));
 __builtin_memcpy(dst+sizeof(ac.regs),&ac.pc,4);
}''').replace('uint64_t *entries){','uint64_t *entries,unsigned char *trace,unsigned stride,unsigned *events){\n ac.trace=trace;ac.stride=stride;ac.events=0;').replace('*entries=ac.entries;return 0;', '*entries=ac.entries;*events=ac.events;return 0;')
# One poll can follow an entry or a back-edge; journal replay needs the
# distinction to reconstruct the original entry ring, including recursion.
s=s.replace('++ac.entries;ac.pc=(va);ngb_guest_block_poll();','++ac.entries;ac.pc=(va)|0x80000000u;ngb_guest_block_poll();ac.pc=(va);')
exec(compile(s,'checkpoint-worker','exec'))
