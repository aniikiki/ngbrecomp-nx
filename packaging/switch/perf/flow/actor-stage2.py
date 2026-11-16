"""Time the subsequent full-pool traversal, not only the sorted-actor pass.
Use the same exclusive task clock and preserve native control flow."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
s=(here/'actor-clock.py').read_text().replace("core-perf/actor-clock","core-perf/actor-stage2").replace("out = work / 'actor-clock'","out = work / 'actor-stage2'").replace("(16,'loc_001CC5F0: ; ngb_guest_block_poll();','loc_001CC62B: ;',1),(10,'loc_00147ECD: ;','loc_00147EE6: ;',2)","(10,'loc_00149654: ;','loc_00149700: ;',3)").replace("'001CC5A0' if i==1 else '00147DF0'","'00149620'").replace("('0010','0016')","('0010',)")
# A fast empty-result exit skips 149700. Place the exit at 149704 and
# start timing all 64 slots, so inactive actors cannot pop the prior context.
s=s.replace("'loc_00149654: ;','loc_00149700: ;'","'loc_00149640: ; ngb_guest_block_poll();','loc_00149704: ;'")
exec(compile(s,'stage-two-clock','exec'))
