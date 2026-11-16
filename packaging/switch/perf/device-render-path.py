"""Disjoint sampled costs within the ordered render tree, using actual device PCs."""
import runpy, sys
from pathlib import Path
from collections import Counter
api=runpy.run_path(str(Path(__file__).resolve().parents[1]/'analyze-profile.py'))
def report(log,symbols):
    sym=api['load_symbols'](symbols)
    windows=api['parse_windows'](Path(log).read_text().splitlines())
    for (lo,hi),w in windows.items():
        if 'guest' not in w['profiles']:continue
        rows=w['profiles']['guest'][1]
        groups=Counter(); callbacks=Counter()
        for f,_,scope,_,_,pcs in rows:
            if not lo<=f<=hi:continue
            st=[sym(pc).removeprefix('ngb_reg_').split('.localalias')[0] for pc in pcs]
            if 'sub_001CA790' not in st:group='other game-thread work'
            elif 'sub_0030BCA0' not in st:group='ordered tree, outside shared mesh'
            elif 'sub_003C9B40' in st:group='mesh: indexed draw (incl. HLE and recording)'
            elif 'sub_0030B7E0' in st:group='mesh: material'
            elif 'sub_0030C240' in st:group='mesh: initial setup'
            else:group='mesh: remaining'
            groups[group]+=1
            if 'sub_001CA790' in st:
                cb=next((x for x in st if x in {'sub_001CB260','sub_001CB3B0','sub_001CB510','sub_001CB550'}),'other')
                callbacks[cb,group]+=1
        print(lo,hi,'guest wall samples',groups.total(),dict(groups))
        if lo==1801:
            for key,n in sorted(callbacks.items()):print(*key,n)
if __name__=='__main__':report(*sys.argv[1:])
