"""Observe adjacent emitted GPU draws; bounds only, no changes to ordering or commands."""
def apply(s,geometry=False,bias=False):
 def once(k,r):
  nonlocal s
  assert s.count(k)==1,k
  s=s.replace(k,r)
 k='    VkShaderModule MakeModule('
 once(k,'''    struct Neighbor {
      VkPipeline pipe{}; bool indexed=false, shortidx=false;
      VkViewport vp{}; VkRect2D sc{}; VkImageView view[4]{}; VkSampler sampler[4]{};
      VkImageLayout layout[4]{}; VkDeviceSize vc{},dc{}; uint32_t blend{}, stencil{};
    } neighbor_;
    unsigned long long neighbor_counts_[6]{};
'''+k)
 k='    d_.vkCmdEndRendering(cmd_);'
 assert s.count(k)==4
 s=s.replace(k,'    neighbor_.pipe=VK_NULL_HANDLE;\n'+k)
 k='    if (n) d_.vkCmdClearAttachments';once(k,'    if(n) neighbor_.pipe=VK_NULL_HANDLE;\n'+k)
 k='    if (a.index_count) {\n        d_.vkCmdBindIndexBuffer'
 once(k,'''    if (presents_<120) {
        Neighbor cur{}; cur.pipe=pipe;cur.indexed=a.index_count!=0;cur.shortidx=cur.indexed && a.index16;
        cur.vp=vpt;cur.sc=sc;cur.vc=vc;cur.dc=dc;
        cur.blend=SimpleState(s,kMBlendColor);cur.stencil=SimpleState(s,kMStencilRef)&255;
        for(int i=0;i<4;++i){cur.view[i]=img[i].imageView;cur.layout[i]=img[i].imageLayout;cur.sampler[i]=smp[i].sampler;}
        auto &last=neighbor_;auto &n=neighbor_counts_;n[0]++;n[1]+=cur.indexed;
        if(!vis_on_ && last.pipe==cur.pipe && last.indexed==cur.indexed && last.shortidx==cur.shortidx){
            n[2]++;
            if(!std::memcmp(&last.vp,&cur.vp,sizeof(cur.vp)) && !std::memcmp(&last.sc,&cur.sc,sizeof(cur.sc))
                 && last.blend==cur.blend && last.stencil==cur.stencil){
                n[3]++;
                if(!std::memcmp(last.view,cur.view,sizeof(cur.view)) && !std::memcmp(last.layout,cur.layout,sizeof(cur.layout))
                   && !std::memcmp(last.sampler,cur.sampler,sizeof(cur.sampler))){
                    n[4]++;if(last.vc==cur.vc && last.dc==cur.dc)n[5]++;
                }
            }
        }
        last=cur;if(vis_on_)last.pipe=VK_NULL_HANDLE;
    }
'''+k)
 k='    presents_++;';once(k,k+r"""
    neighbor_.pipe=VK_NULL_HANDLE;
    if(presents_==30||presents_==120){
      auto &n=neighbor_counts_;std::fprintf(stderr,"[DRAW_NEIGHBORS] %u draws=%llu indexed=%llu pipe=%llu dynamic=%llu textures=%llu constants=%llu\n",presents_,n[0],n[1],n[2],n[3],n[4],n[5]);
      std::memset(n,0,sizeof(n));
    }
""")
 if geometry:
  once('unsigned long long neighbor_counts_[6]{};', 'unsigned long long neighbor_counts_[9]{};')
  once('uint32_t blend{}, stencil{};', """uint32_t blend{}, stencil{}, nb{}; VkBuffer geom[16]{},ib{};
      VkDeviceSize off[16]{},indexoff{};uint32_t stride[16]{};""")
  once('auto &last=neighbor_;', """cur.nb=a.buffer_count;cur.ib=index_buf;cur.indexoff=ioff;
        for(unsigned b=0;b<cur.nb;b++){cur.geom[b]=bufs[b];cur.off[b]=voff[b];cur.stride[b]=a.buffers[b].stride;}
        auto &last=neighbor_;""")
  once('if(last.vc==cur.vc && last.dc==cur.dc)n[5]++;', """if(last.vc==cur.vc && last.dc==cur.dc){
                     n[5]++; if(cur.indexed && !Lines(k) && !(k.has_ds & kDsDynamicBias) && cur.nb==last.nb &&
                           cur.ib==last.ib && (cur.indexoff%(cur.shortidx?2:4))==(last.indexoff%(cur.shortidx?2:4))){
                       n[6]++;bool exact=true,fit=true;int64_t delta=0;bool have_delta=false;
                       for(unsigned b=0;b<cur.nb;b++){
                          if(cur.geom[b]!=last.geom[b] || cur.stride[b]!=last.stride[b]){fit=exact=false;break;}
                          int64_t bytes=int64_t(cur.off[b])-int64_t(last.off[b]);
                          exact=exact && !bytes;
                          if(!cur.stride[b]){if(bytes)fit=false;continue;}
                          if(bytes%cur.stride[b]){fit=false;continue;}
                          int64_t q=bytes/cur.stride[b];if(have_delta && delta!=q)fit=false;
                          delta=q;have_delta=true;
                       }
                       if(fit && int64_t(a.base_vertex)+delta>=INT32_MIN && int64_t(a.base_vertex)+delta<=INT32_MAX)n[7]++;
                       if(exact)n[8]++;
                     }
                  }""")
  once('std::memset(n,0,sizeof(n));','std::fprintf(stderr,"[GEOM_NEIGHBORS] %u compatible_index=%llu vertex_rebase=%llu vertex_exact=%llu\\n",presents_,n[6],n[7],n[8]);std::memset(n,0,sizeof(n));')
 if bias:
  assert geometry
  once('uint32_t stride[16]{};', 'uint32_t stride[16]{};float bias_units{},bias_slope{},width{};')
  once('cur.nb=a.buffer_count;',"""if(k.has_ds & kDsDynamicBias){cur.bias_units=float(k.zbias + pull_steps);cur.bias_slope=k.zslope+pull_slope;}
        if(Lines(k))cur.width=wide_lines_ ? std::clamp(Bits(s.rs[kRsLineWidth])*sx*(Bits(s.rs[kRsLineWidth])>1.0f?SparkWidth():1.0f),1.0f,line_max_) : 1.0f;
        cur.nb=a.buffer_count;""")
  once('!Lines(k) && !(k.has_ds & kDsDynamicBias)', 'cur.bias_units==last.bias_units && cur.bias_slope==last.bias_slope && cur.width==last.width')
 return s
