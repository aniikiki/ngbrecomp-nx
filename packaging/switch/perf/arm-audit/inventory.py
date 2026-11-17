"""Run after spans.py, from the repository root; outputs only locations and metadata."""
import collections, pathlib, re, struct, sys
D = pathlib.Path(sys.argv[1])
nro = pathlib.Path('build/switch-runtime/history/0.56.23/ngb-startup.nro').read_bytes()
rows = [l.split() for l in (D/'spans').read_text().splitlines()]
linked = {sec.removeprefix('.text.') for _, _, group, sec in rows if group != 'glue'}
with (D/'indirect.tsv').open('w') as f:
    print('unit\tsection\tnro_pc\top\tregister', file=f)
    for start, size, group, sec in rows:
        for pc in range(int(start), int(start)+int(size), 4):
            w, = struct.unpack_from('<I', nro, pc)
            op = {0xd61f0000:'BR', 0xd63f0000:'BLR'}.get(w & 0xfffffc1f)
            if op:
                print(group, sec, hex(pc), op, (w>>5)&31, sep='\t', file=f)
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
xbe=pathlib.Path('game_files/default.xbe').read_bytes()
u=lambda off: struct.unpack_from('<I',xbe,off)[0]
sections=[struct.unpack_from('<4I',xbe,u(0x120)-u(0x104)+56*i+4) for i in range(u(0x11c))]
dis=Cs(CS_ARCH_X86, CS_MODE_32)
def candidates(start,condition):
    for va,_,offset,size in sections:
        if va<=start<va+size:
            at=offset+start-va
            for ins in dis.disasm(xbe[at:min(at+4096,offset+size)],start):
                if ins.mnemonic==condition:return hex(ins.address)
                if ins.mnemonic.startswith(('j','ret')):break
    return '-'
with (D/'flag-sites.tsv').open('w') as f:
    print('unit\tguest_function\tguest_block\tgenerated_line\tcondition\tlinked_section\txbe_pc_from_block', file=f)
    for p in sorted(pathlib.Path('build/switch-runtime/gen').glob('recomp_*.c')):
        s=p.read_text()
        for m in re.finditer(r'^void (sub_[0-9A-F]+)\(void\)\n\{(.*?)^\}', s, re.M|re.S):
            body=m[2]
            if not re.search(r'int _flags\s*=\s*0', body): continue
            for j in re.finditer(r'(_flags)\s*/\*\s*(\w+)',body):
                other=re.sub(r'int _flags\s*=\s*0|/\*.*?\*/','',body,flags=re.S)
                if re.search(r'_flags\s*[+*/&|^!<>-]*=(?!=)',other):continue
                labels=re.findall(r'loc_([A-F0-9]+):',body[:j.start()])
                print(p.stem,m[1],labels[-1] if labels else '-',s.count('\n',0,m.start(2)+j.start())+1,j[2],int(m[1] in linked),candidates(int(labels[-1],16),j[2]) if labels else '-',sep='\t',file=f)
mask=(D/'mask').read_bytes()
linkmap=(D/'linked.map').read_text()
with (D/'tables.tsv').open('w') as out:
    print('unit\tsection\tnro_br\tentries\tdistinct_targets',file=out)
    for line in (D/'indirect.tsv').read_text().splitlines()[1:]:
        group, sec, p, op, reg=line.split()
        if group=='glue':continue
        pc=int(p,16)
        data=re.search(r'^ '+re.escape(sec.replace('.text.', '.rodata.'))+r'\s+(0x\w+)\s+(0x\w+)',linkmap,re.M)
        assert data and op=='BR'
        addr,n=(int(i,16) for i in data.groups())
        a,add,ldr,adr,extend=struct.unpack_from('<5I',nro,pc-20)
        imm=((a>>29)&3)|(((a>>5)&0x7ffff)<<2)
        page=((pc-20)&~4095)+((imm^0x100000)-0x100000)*4096
        assert page+((add>>10)&4095)==addr and adr==0x10000060
        size={0x38604800:1,0x78605800:2}[ldr&0xfffffc00]
        assert not n%size
        lo,sz=next((int(s),int(z)) for s,z,g,c in rows if g==group and c==sec)
        targets=[pc+4+4*k[0] for k in struct.iter_unpack('<b' if size==1 else '<h',nro[addr:addr+n])]
        assert all(lo<=x<lo+sz and mask[x//4] for x in targets)
        print(group,sec,p,len(targets),len(set(targets)),sep='\t',file=out)
