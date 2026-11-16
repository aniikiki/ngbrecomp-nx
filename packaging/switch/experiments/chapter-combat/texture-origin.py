"""Host only: correlate completed AFS reads with actual new texture uploads."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('chapter-texture-origin')
def sub(s,k,v):
    assert s.count(k)==1,k
    return s.replace(k,v)
clk='''static unsigned long long tex_now(void){struct timespec x;clock_gettime(CLOCK_MONOTONIC,&x);return (unsigned long long)x.tv_sec*1000000000+x.tv_nsec;}'''
s=(RUNTIME/'files.c').read_text()
s=sub(s,'uint32_t ngb_file_read(',clk+'\nuint32_t ngb_file_read(')
k='    if (ferror(handles[i].file)) return error_status();'
i=s.index(k,s.index('*received = (uint32_t)fread(buffer'))
s=s[:i]+'''    if (*received && strstr(handles[i].path,".afs")) fprintf(stderr,"[TXREAD] %llu %s %lld %u\\n",tex_now(),ngb_file_basename(handle),(long long)ftello(handles[i].file)-*received,*received);
'''+s[i:]
idx=next(i for i,x in enumerate(p.link) if x.endswith('/files.c.o'))
p.link[idx]=p.compile('files.c','#include <time.h>\n'+s)
s=(ROOT/'src/d3d/vk/backend.cpp').read_text()
s=sub(s,'VkImageView VulkanBackend::BindTexture(',clk+'\nVkImageView VulkanBackend::BindTexture(')
k='    if (tx.img.image) Retire(tx.img);'
s=sub(s,k,'''    auto tex_start=tex_now(); bool replaced=!!tx.img.image;
'''+k)
k='    tx.info = info;'
s=sub(s,k,'''    auto tex_end=tex_now();
    if(bytes>=32){
        unsigned long long h=14695981039346656037ull;
        for(unsigned i=0;i<bytes;i++){h^=guest[i];h*=1099511628211ull;}
        char sample[65];unsigned at=(bytes-32)/2;
        for(unsigned i=0;i<32;i++)std::sprintf(sample+2*i,"%02x",guest[at+i]);
        std::fprintf(stderr,"[TXUPLOAD] %llu %u %x %u %u %llx %s %d %llu\\n",tex_start,frame_,d.data,bytes,at,h,sample,int(replaced),tex_end-tex_start);
    }
'''+k)
p.link[p.link.index(str(REGS/'backend-host-clip.o'))]=p.compile('vk/backend.cpp','#include <time.h>\n'+s,['-DNGB_RIGID_CLIP'])
p.driver('');p.link.insert(1,'-Wl,--strip-debug');p.finish()
