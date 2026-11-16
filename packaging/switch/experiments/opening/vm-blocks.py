"""Publish full 64KiB VM groups for a measured two-MiB window, never assume mapped."""
from pathlib import Path
def vm(s):
    key='uint32_t opening_end4[1u<<20];'
    assert s.count(key)==1
    s=s.replace(key,key+'''
uint32_t opening_full_groups;
static void refresh_groups(unsigned first,unsigned count){
    if(first>=512 || !count)return;
    unsigned end=first+count; if(end>512)end=512;
    for(unsigned group=first/16; group<=(end-1)/16; ++group){
        uint32_t bit=1u<<group; unsigned i=0;
        while(i<16 && opening_end4[4096+group*16+i])++i;
        opening_full_groups=(opening_full_groups & ~bit) | (i==16?bit:0u);
    }
}
''')
    k='    memset(opening_end4,0,sizeof opening_end4);';assert s.count(k)==1
    s=s.replace(k,'    opening_full_groups=0;\n'+k)
    k='    *base = ';a=s.index('uint32_t ngb_vm_query')
    assert s[:a].count(k)==2
    return s[:a].replace(k,'    refresh_groups(first,count);\n'+k)+s[a:]
def header(s):
    k='        if (__builtin_expect(address < reg_ends[address>>12],1))'
    assert s.count(k)==1
    return s.replace(k,'''        extern uint32_t opening_full_groups;
        uint32_t off=address-0x01000000u;
        if(off<0x00200000u && (off&65535u)<=65536u-bytes &&
           ((opening_full_groups>>(off>>16)) & 1u))
            return (uintptr_t)ngb_fast_ram+address;
'''+k)
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text()
    a=s.index('next_set=');b=s.index('parent=d.parent',a)
    s=s[:a]+"next_set=loop_ira=False\nd=(base/'core-perf/opening-vm-blocks').resolve();d.mkdir(exist_ok=True)\n"+s[b:]
    s=s.replace("(parent/'template.h').read_text()", "header((parent/'template.h').read_text())")
    s=s.replace("assert (d/'guest_memory.h').read_bytes()==(parent/'guest_memory.h').read_bytes()","assert (d/'guest_memory.h').read_text()==header((parent/'guest_memory.h').read_text())")
    import sys
    instrument=header
    if '--census' in sys.argv:
        s=s.replace('opening-vm-blocks','opening-vm-block-census')
        def instrument(t):
            t=header(t)
            a=t.index('        if(off<');b=t.index('        if (__builtin_expect(address < reg_ends',a)
            return t[:a]+'''        extern unsigned vb_active;
        extern unsigned long long vb_bins[5];
        unsigned cat=off>=0x200000u ? (address>=0x80000000u?4:3) :
                     (off&65535u)>65536u-bytes ? 2 :
                     ((opening_full_groups>>(off>>16))&1u) ? 0 : 1;
        if(vb_active)++vb_bins[cat];
        if(!cat)return (uintptr_t)ngb_fast_ram+address;
'''+t[b:]
    exec(compile(s,'vm-blocks-build','exec'),{'header':instrument})
