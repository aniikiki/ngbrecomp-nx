"""Match a real upload to the bytes nominated by an on-disc KMD/XPR texture descriptor.
Only count a unique source file, and require completed reads of both the header and all pixel bytes.
"""
import re,sys,struct,statistics
from pathlib import Path
from collections import defaultdict
log=Path(sys.argv[1]).read_text(errors='replace')
reads=defaultdict(list)
for t,name,pos,n in re.findall(r'^\[TXREAD\] (\d+) (\S+) (\d+) (\d+)',log,re.M):
    reads[name.lower()].append((int(t),int(pos),int(pos)+int(n)))
uploads={}
for t,f,addr,n,at,h,sample,repl,work in re.findall(r'^\[TXUPLOAD\] (\d+) (\d+) (\w+) (\d+) (\d+) (\w+) (\w+) (\d+) (\d+)',log,re.M):
    if repl=='0':uploads.setdefault((int(n),int(h,16)),(int(t),int(f),bytes.fromhex(sample),int(at),int(work)))
def ready(events,start,end,before):
    spans=[]
    for t,a,b in reversed(events):
        if t>before:continue
        if a>=end or b<=start:continue
        spans.append((max(a,start),min(b,end)));cursor=start
        for x,y in sorted(spans):
            if x>cursor:break
            cursor=max(cursor,y)
        if cursor==end:return max(q for q,u,v in events if t<=q<=before and u<end and v>start)
def digest(buf):
    h=14695981039346656037
    for v in buf:h=((h^v)*1099511628211)&0xffffffffffffffff
    return h
matches=defaultdict(list)
for name,events in reads.items():
    path=Path('game_files')/name
    if name in ('bgm.afs','sse.afs') or not path.exists():continue
    b=path.read_bytes()
    if b[:4]!=b'AFS\0':continue
    for j in range(int.from_bytes(b[4:8],'little')):
        o,z=struct.unpack_from('<II',b,8+8*j)
        if b[o:o+4]!=b'KMD\0':continue
        x=b.find(b'XPR0',o,o+z)
        if x<0:continue
        total,head=struct.unpack_from('<II',b,x+4)
        if not 12<=head<=total<=o+z-x:continue
        for i in range(x+12,x+head-19,4):
            common,off,lock,fmt,size=struct.unpack_from('<IIIII',b,i)
            if common!=0x40001 or lock or (fmt>>4)&15 not in (2,3):continue
            pix=x+head+off
            for key,(t,f,pat,at,work) in uploads.items():
                n,h=key
                if pix+n>x+total or b[pix+at:pix+at+32]!=pat:continue
                ht=ready(events,x,x+head,t)
                if not ht:continue
                pt=ready(events,pix,pix+n,t)
                if not pt or max(pt,ht)>t or digest(b[pix:pix+n])!=h:continue
                matches[key].append((name,j,f,(t-max(pt,ht))/1e6))
byfile=defaultdict(list); output=[]
for key,vs in matches.items():
    if len({v[0] for v in vs})==1:
        v=min(vs,key=lambda v:v[-1]);byfile[v[0]].append(v);output.append((v[0],v[1],v[2],key[0],round(v[3],3),round(uploads[key][4]/1e6,4)))
print('story verified:', 'reason=verified first chapter player control' in log,'distinct first upload contents:',len(uploads),'matched:',len(matches))
for name,vs in sorted(byfile.items()):
    times=[v[-1] for v in vs]
    print(name,len(vs),'read-to-upload ms min/median/max',*(round(x,1) for x in (min(times),statistics.median(times),max(times))),'first render frame',min(v[2] for v in vs))

if len(sys.argv)>2:
    import csv
    with open(sys.argv[2],'w',newline='') as out:
        w=csv.writer(out);w.writerow(['archive','member','first_upload_render_frame','bytes','latest_complete_read_to_upload_ms','host_upload_recording_ms']);w.writerows(sorted(output))
