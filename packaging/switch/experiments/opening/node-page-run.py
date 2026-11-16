"""Walk mapped nodes until a service, unusual mapping, or original exit."""
from pathlib import Path
def transform(s):
    key='loc_001CC7F8: ; ngb_guest_block_poll();'
    assert s.count(key)==1
    return s.replace(key, """loc_001CC7F8: ;
    {
        unsigned mask=ngb_poll_mask, off=ecx&4095u, page=ecx>>12;
        unsigned room=mask-((unsigned)ngb_guest_polls&mask);
        unsigned bytes=ngb_fast_page_bytes[page];
        if (room>=2 && !(mask&(mask+1u)) && !ngb_pending_dpcs &&
            !(ecx&3u) && off+16u<=bytes) {
            unsigned char *base=ngb_fast_ram+((ecx&0x7fffffffu)-off);
            unsigned done=0;
            do {
                volatile uint32_t *node=(volatile uint32_t*)(base+off);
                ++done; _fa=node[3]; _fb=ebp; _fas=(int32_t)_fa; _fbs=(int32_t)_fb;
                if(CMP_AE(_fa,_fb)){ngb_guest_polls+=done;goto loc_001CC82E;}
                ecx=node[1]; _fa=ecx; _fb=0; _fas=(int32_t)_fa; _fbs=0;
                if(!ecx){ngb_guest_polls+=done;goto loc_001CC804;}
                off=ecx&4095u;
            } while(done<room && (ecx>>12)==page && !(off&3u) && off+16u<=bytes);
            ngb_guest_polls+=done;
            goto loc_001CC7F8;
        }
    }
    ngb_guest_block_poll();""")
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-node-page-run'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'node-page-run','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-node-page-run/recomp_0016.c').unlink()
