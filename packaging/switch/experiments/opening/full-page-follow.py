"""Decision after the broad ABI experiment: retain coverage only if integrity
and comparable natural-opening CPU timings support further testing."""
from pathlib import Path
import subprocess as sp,sys,re,shutil,runpy
p=Path('packaging/switch/experiments/opening');d=Path('build/switch-runtime/core-perf/wide-start')
result=runpy.run_path(str(p/'follow-results.py'))['outcome']
r=result('full-guest')
if r['valid_runs']!=8 or r.get('errors'):sys.exit('Full guest ABI did not qualify: '+str(r))
pairs=r['pairs']
if any(not (.96<x[1]<1.04 and .96<x[3]<1.04) for x in pairs):sys.exit('Guest workload differed: '+str(pairs))
if min(r['mean_host_cpu_saved_fraction'])<-.015:sys.exit('Full guest register coverage regressed: '+str(pairs))
if shutil.disk_usage('.').free<12*1024**3:sys.exit('Skipping optional build: insufficient disk reserve')
def cmd(image,args):
 sp.run(['docker','run','--rm','-v',str(Path.cwd())+':/work','-w','/work',image,*args],check=True)
cmd('ngb-switch-nxvk:dev',['python3',str(p/'page-limit.py'),'--all-units'])
cmd('ngb-switch-host:direct0331',['timeout','16m','sh',str(p/'run-page-limit.sh'),'--full-page'])
sp.run([sys.executable,str(p/'target-gap.py'),'full-page'],check=True)
