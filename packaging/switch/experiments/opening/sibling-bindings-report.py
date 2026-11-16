"""Final game-draw bindings for consecutive actual siblings, not neighboring pointers."""
from pathlib import Path
from struct import Struct
from collections import Counter
d=Path('build/switch-runtime/core-perf/opening-clip-siblings')
log=(d/'joined.log').read_text()
assert 'original opening motion verified at 120' in log and 'reason=finished joined opening' in log
def rows(name,fmt):
    return list(Struct('<'+fmt).iter_unpack((d/(name+'.bin')).read_bytes()))
prod=rows('producer','9I')
draw=dict(rows('draw','II'))
bindrows=rows('bindings','14Q')
bind={r[0]:r for r in bindrows}
assert len(bind)==len(bindrows) and set(draw)=={i for i,f,key,pc,n,*_ in prod if n}
assert all(i in draw and not draw[i]&2 for i in bind)
stats=[Counter(),Counter()]
prev=None
for seq,(i,f,key,pc,n,ns,index,count,base) in enumerate(prod,1):
    assert i==seq and n<=1
    stats[f>30]['model_draws']+=i in bind
    if pc!=0x3079cc:
        prev=None
        continue
    st=stats[f>30]
    cur=bind.get(i)
    if index:
        assert prev and prev[:4]==(f,base,count,index-1)
        old=prev[4]
        st['siblings']+=1
        if cur and old and cur[1]==old[1]+1:
            st['both_drew_consecutively']+=1
            vc=cur[2:4]==old[2:4]
            dc=cur[2]==old[2] and cur[4]==old[4]
            pipe=cur[5]==old[5]
            views=cur[6:10]==old[6:10]
            sam=cur[10:14]==old[10:14]
            st.update(vc=vc,dc=dc,pipe=pipe,views=views,sam=sam,
                      both_constants=vc and dc,all_observed=vc and dc and pipe and views and sam,
                      only_views_differ=vc and dc and pipe and sam and not views)
            for stage in range(4):
                st[f'view_changed_{stage}']+=cur[6+stage]!=old[6+stage]
            st['changed_views_'+str(sum(a!=b for a,b in zip(cur[6:10],old[6:10])))]+=1
    prev=(f,base,count,index,cur)
for s in stats: print(dict(sorted(s.items())))
