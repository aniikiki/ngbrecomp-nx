from pathlib import Path
import re,runpy
base=Path('build/switch-runtime')
gen=(base/'gen/recomp_0010.c').read_text()
labels=runpy.run_path(str(Path(__file__).with_name('contact-blocks.py')))['transform'](gen)[1]
s=(base/'core-perf/opening-contact-blocks/distribution.log').read_text()
assert 'verified 120 original demo frames' in s
rows=re.findall(r'^\[CONTACT_BLOCKS\] (30|120) ([0-9 ]+)$',s,re.M);assert [int(f) for f,_ in rows]==[30,120]
for f,row in rows:
 vals=list(map(int,row.split()));assert len(vals)==256 and not any(vals[len(labels):])
 c=dict(zip(labels,vals));print('window end',f,'calls',c['00140AF0'],'scan iterations',c['00140FF2'],'top visited labels',sorted(c.items(),key=lambda x:-x[1])[:14])
