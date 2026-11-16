"""Sparse worker with poll register snapshots, no per-write journal. Offline
hypothesis: actor stores are private until the end of a job. Runtime consumer
must prove isolation independently; not a general-purpose replacement."""
from pathlib import Path
h=Path(__file__).resolve().parent;s=(h/'sparse.py').read_text();a=s.index("exec(compile(s,'sparse-actor")
s=s[:a]+'''s=s.replace('opt050/actor-sparse','opt050/actor-wave-state')
s=s.replace('unsigned pc,error,used;', 'uint8_t*trace;unsigned events;unsigned pc,error,used;')
s=s.replace('unsigned *used,uint8_t *foot){','unsigned *used,uint8_t *foot,uint8_t *trace){ac.trace=trace;ac.events=0;')
s=s.replace('static inline void ngb_guest_block_poll(void){++ac.polls;}',"""static inline void ngb_guest_block_poll(void){
 ++ac.polls;if(++ac.events>=8192){ac.error=~0u;longjmp(ac.unwind.escape,1);}
 unsigned char *dst=ac.trace+ac.events*320u;__builtin_memcpy(dst,&ac.regs,sizeof(ac.regs));__builtin_memcpy(dst+sizeof(ac.regs),&ac.pc,4);}""")
s=s.replace('++ac.entries;ac.pc=(va);ngb_guest_block_poll();','++ac.entries;ac.pc=(va)|0x80000000u;ngb_guest_block_poll();ac.pc=va;')
s=s.replace('#define ngb_pending_dpcs 0u','#define ngb_pending_dpcs 1u')
s=s.replace("scan=(r/'scan_tags.inc').read_text()", "scan='/* expose every original poll */'")
# The sparse builder generated matrix.h with a validated pair of 64 B spans.
# Keep that file beside this recompiled object's other private headers.
q=Path('/work/build/switch-runtime/opt050/actor-wave-state');q.mkdir(exist_ok=True)
(q/'worker_matrix.h').write_text(p.read_text())
'''+s[a:];exec(compile(s,'wave-state-generator','exec'))
