# Reuse the public/private/foreign calling convention harness with this candidate's actual guard.
from pathlib import Path
import runpy
p=Path(__file__).resolve().parent
s=(p/'compact-bridges-check.py').read_text().replace('opening-full-guest','opening-full-page')
a=s.index('entry,gates=');b=s.index('gates=gates[',a)
s=s[:a]+'''entry=s[a:b]+'.size xbe_entry_point,.-xbe_entry_point\\n'
gates=(base/'gates.s').read_text()
'''+s[b:]
s=s.replace('with tempfile.TemporaryDirectory()', '''entry+='\\n.text\\n'+runpy.run_path(str(p/'gate-sites.py'))['guard']('test_guard','xbe_entry_point')
driver=driver.replace('bl ngb_gate_indirect','bl test_guard').replace('ngb_fast_page_bytes','opening_end4')
with tempfile.TemporaryDirectory()''')
exec(compile(s,'gate-sites-check','exec'))
