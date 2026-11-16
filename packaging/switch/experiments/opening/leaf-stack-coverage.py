"""Screen function-wide stack translation by measured word references before building clones."""
from pathlib import Path
import contextlib,io,runpy,re,collections
with contextlib.redirect_stdout(io.StringIO()):
 d=runpy.run_path(str(Path(__file__).with_name('word-site-owners.py')))
bodies={}
for u in d['obs']['units']:
 s=(d['base']/f'gen/recomp_{u:04}.c').read_text()
 for m in re.finditer(r'^void (\w+)\(void\)\n\{(.*?)^\}',s,re.S|re.M):bodies[m[1]]=m[2]
bins=collections.Counter();byfn=collections.defaultdict(collections.Counter)
for (fn,raw),count in d['ops'].items():
 if not re.search(r'\b(?:PUSH32|POP32)\(esp,|\bMEM32\(esp(?:\s*[+-]|\))',raw):continue
 b=bodies[fn];call=bool(re.search(r'RECOMP_(?:ABI_CALL|ICALL|ITAIL)|\bsub_[0-9A-F]+\(',b))
 poll='ngb_guest_block_poll()' in b
 bins[call,poll]+=count
 byfn[call,poll][fn]+=count
allrefs=sum(d['owners'].values())
for k,n in sorted(bins.items()):print('call,block poll',k,'stack-word candidates/frame',round(n/90), 'of all word refs',round(100*n/allrefs,2))
for k,c in sorted(byfn.items()):print(k,[(fn,round(n/90)) for fn,n in c.most_common(5)])
