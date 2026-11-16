"""Walk mapped nodes until a service, unusual mapping, or original exit."""
from pathlib import Path
def transform(s):
    key='loc_001CC7F8: ; ngb_guest_block_poll();'
    assert s.count(key)==1
    return s.replace(key, """loc_001CC7F8: ;
    for (;;) {
        uint64_t t = ngb_guest_polls + 1;
        if (!(t & ngb_poll_mask) || ngb_pending_dpcs) break;
        uint32_t off = ecx & 4095u;
        if ((ecx & 3u) || off + 16u > ngb_fast_page_bytes[ecx >> 12]) break;
        volatile uint32_t *node = (volatile uint32_t *)(ngb_fast_ram + (ecx & 0x7fffffffu));
        ngb_guest_polls = t;
        _fa = node[3]; _fb = ebp; _fas = (int32_t)_fa; _fbs = (int32_t)_fb;
        if (CMP_AE(_fa,_fb)) goto loc_001CC82E;
        ecx = node[1];
        _fa = ecx; _fb = 0; _fas = (int32_t)_fa; _fbs = 0;
        if (!ecx) goto loc_001CC804;
    }
    ngb_guest_block_poll();""")
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-node-walk'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'node-walk','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-node-walk/recomp_0016.c').unlink()
