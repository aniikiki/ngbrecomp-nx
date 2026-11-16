"""Join exact-eligible comparison sites to real guest entries; no assumption a site executed."""
from collections import Counter
from pathlib import Path
import re,runpy
p=Path(__file__).parent; trans=runpy.run_path(str(p/'ordered-branch.py'))['transform']
d=Path('build/switch-runtime'); owners={}
for f in (d/'gen').glob('recomp_*.c'):
 s=f.read_text()
 for m in re.finditer(r'^void sub_([0-9A-F]+)\(void\)\n\{.*?^\}',s,re.M|re.S):
  body=m[0];delta=trans(body,0).count('if (((_fa & 0x44u) != 0x40u)) goto')-body.count('if (((_fa & 0x44u) != 0x40u)) goto')
  if delta:owners[int(m[1],16)]=delta
log=(d/'core-perf/opening-guest-sites/budget.log').read_text()
assert 'verified 120 original demo frames' in log
print('owners',len(owners),'sites',sum(owners.values()))
for end in (30,120):
 traffic=Counter()
 for va,n in re.findall(r'^\[GUEST_SITE\] '+str(end)+r' \w+ (\w+) (\d+)$',log,re.M):
  if int(va,16) in owners: traffic[int(va,16)]+=int(n)
 print(end,'observed function entries',sum(traffic.values()),'active owners',len(traffic),'top',[(hex(k),v,owners[k]) for k,v in traffic.most_common(6)])
