"""Count original FIFO header fallbacks, not per-parameter iterations or elapsed time."""
from pathlib import Path
def install(p,rt,src):
 s=(rt/'nv2a_boot.c').read_text()
 key='static void execute_dma(uint32_t put)'
 assert s.count(key)==1
 s=s.replace(key,'''static unsigned inspect_dma_headers;
static struct {unsigned packets; unsigned long long params;} mix[2][2048];
static unsigned other, already_classified;
void mix_dma_phase(unsigned f){
 if(f==30){inspect_dma_headers=1;}
 if(f==120){
  inspect_dma_headers=0;
  for(unsigned t=0;t<2;t++) for(unsigned m=0;m<2048;m++) if(mix[t][m].packets)
   fprintf(stderr,"[DMA_FALLBACK] %u %x %u %llu\\n",t,m*4,mix[t][m].packets,mix[t][m].params);
  fprintf(stderr,"[DMA_MISC] %u %u\\n",other,already_classified);
 }
}
'''+key)
 key='        uint32_t type = word & 0xe0030003u;';assert s.count(key)==1
 s=s.replace(key,key+'''
        if(inspect_dma_headers){
         unsigned sub=(word>>13)&7u,m=(word&NV_PFIFO_CACHE1_DMA_STATE_METHOD)>>2;
         if((type==0 || type==0x40000000u) && !sub && m<2048 &&
            (graph_regs[NV_PGRAPH_CTX_CACHE1/4]&255)==NV_KELVIN_PRIMITIVE){
          if(state_packet_size(word)) ++already_classified;
          else {unsigned t=type!=0;++mix[t][m].packets;mix[t][m].params+=(word>>18)&2047u;}
         }else ++other;
        }''')
 idx=[i for i,x in enumerate(p.link) if x.endswith('/nv2a_boot.c.o')];assert len(idx)==1
 p.link[idx[0]]=p.compile('nv2a_boot.c',s)
 k='void angle_boundary(unsigned f, unsigned draws) {';assert src.count(k)==1
 return src.replace(k,'extern void mix_dma_phase(unsigned);\n'+k+'mix_dma_phase(f);')
