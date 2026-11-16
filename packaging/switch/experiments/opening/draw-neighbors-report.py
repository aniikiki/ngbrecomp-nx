from pathlib import Path
import re
d=Path('build/switch-runtime/core-perf/opening-present-combined')
for arm in ('neighbors','geomneighbors','biasneighbors'):
    s=(d/f'{arm}-base-1.log').read_text()
    assert 'reason=verified 120 original demo frames' in s
    def rows(tag):
        return {int(f):dict((k,int(n)) for k,n in re.findall(r'(\w+)=(\d+)',payload)) for f,payload in re.findall(r'^\['+tag+r'\] (\d+) (.*)$',s,re.M)}
    r=rows('DRAW_NEIGHBORS');g=rows('GEOM_NEIGHBORS')
    assert set(r)=={30,120} and (not g if arm=='neighbors' else set(g)==set(r))
    for f,v in r.items():
        vals=[v[k] for k in ('draws','pipe','dynamic','textures','constants')]
        assert vals==sorted(vals,reverse=True)
        if g:
            i,b,x=[g[f][k] for k in ('compatible_index','vertex_rebase','vertex_exact')]
            assert 0<=x<=b<=i<=min(v['indexed'],v['constants'])
            print(arm, f, b,'rebased pairs /',v['indexed'],'indexed draws;',round(b/(30 if f==30 else 90),2),'per frame;',round(100*b/v['indexed'],2),'%')
        else:print(arm, f, vals)
