"""Classify actual changed bytes and snapshot commands between adjacent title draws."""
def transform(s, shader_detail=False,strip_detail=False,footprint=False):
    def once(old,new):
        nonlocal s
        assert s.count(old)==1,old
        s=s.replace(old,new)
    once('class Recorded final : public Backend {','''extern "C" void draw_sep_pair(unsigned,unsigned);
extern "C" unsigned draw_sep_epoch(void);
class Recorded final : public Backend {
    unsigned sep_epoch_=~0u,sep_mask_=0,sep_prim_=0;
    bool sep_count_=false,sep_prev_=false,sep_index_=false;
    void SepDiff(size_t off,const uint8_t* now,size_t len){
      if(!sep_count_)return;
      const auto *old=reinterpret_cast<const uint8_t*>(&sent_);
      for(size_t j=off;j<off+len;j++)if(now[j]!=old[j]){
        if(j>=offsetof(State,vsc)&&j<offsetof(State,vsc)+sizeof(State::vsc))sep_mask_|=1;
        else if(j>=offsetof(State,streams)&&j<offsetof(State,vs_handle))sep_mask_|=2;
        else if(j>=offsetof(State,textures)&&j<offsetof(State,streams))sep_mask_|=4;
        else if(j>=offsetof(State,transforms)&&j<offsetof(State,material))sep_mask_|=8;
        else sep_mask_|=16;
      }
    }
''')
    once('        SendState(s, start + count);','''        unsigned ep=draw_sep_epoch();
        sep_mask_=0;sep_count_=ep!=0;
        bool pair=sep_prev_ && sep_epoch_==ep;
        SendState(s, start + count);
        sep_count_=false;
        if(ep)draw_sep_pair(pair?sep_mask_:256,
            pair && indices && sep_index_ && prim==sep_prim_);
        sep_epoch_=ep;sep_prev_=true;sep_prim_=prim;sep_index_=indices!=nullptr;''')
    once('        std::memcpy(reinterpret_cast<uint8_t*>(&sent_) + off,','        SepDiff(off,now,bytes);\n        std::memcpy(reinterpret_cast<uint8_t*>(&sent_) + off,')
    for op,bit in [('Headers',32),('Peek',64)]:
        once('Cmd c{Op::'+op+'};','if(sep_count_)sep_mask_|='+str(bit)+';\n        Cmd c{Op::'+op+'};')
    for sig in ('        if (s.vs.get() != sent_.vs.get()) {','        if (s.ps.get() != sent_.ps.get()) {'):
        once(sig,sig+'\n            if(sep_count_)sep_mask_|=128;')
    for op in ('Clear','Copy','Present','Flush','Gamma','VisBegin','VisEnd'):
        key='Cmd c{Op::'+op+'};' if 'Cmd c{Op::'+op+'};' in s else 'cur_->cmds.push_back(Cmd{Op::'+op+'});'
        once(key,'sep_prev_=false;\n        '+key)
    if shader_detail:
        once('unsigned sep_epoch_', 'unsigned sep_shader_=0;\n    unsigned sep_epoch_')
        once('sep_mask_=0;sep_count_=', 'sep_mask_=0;sep_shader_=0;sep_count_=')
        once('extern "C" void draw_sep_pair(unsigned,unsigned);','extern "C" void draw_sep_shader(unsigned);\nextern "C" void draw_sep_pair(unsigned,unsigned);')
        once('sep_epoch_=ep;sep_prev_=true;', 'if(ep && pair && indices && sep_index_ && prim==sep_prim_ && sep_mask_==128)draw_sep_shader(sep_shader_);\n        sep_epoch_=ep;sep_prev_=true;')
        key='if (s.ps.get() != sent_.ps.get()) {'
        once(key,key+"""
            if(sep_count_)sep_shader_|= !s.ps || !sent_.ps ? 1u :
                std::memcmp(s.ps->def,sent_.ps->def,sizeof s.ps->def) ? 2u : 4u;""")
        key='if (s.vs.get() != sent_.vs.get()) {'
        once(key,key+"""
            if(sep_count_)sep_shader_|= !s.vs || !sent_.vs ? 8u :
                (s.vs->program_type!=sent_.vs->program_type || s.vs->program!=sent_.vs->program || s.vs->decl!=sent_.vs->decl) ? 16u : 32u;""")
    if strip_detail:
        once('extern "C" void draw_sep_pair(unsigned,unsigned);','extern "C" void sep_strip_reason(unsigned);\nextern "C" void draw_sep_pair(unsigned,unsigned);')
        key='            Cmd& prev = cur_->cmds.back();'
        once(key,key+"""
            if(ep)sep_strip_reason(prim!=6 ? 1 : prev.a!=prim ? 2 : !indices ? 3 : prev.d!=1 ? 4 :
                prev.b!=start ? 5 : count<3||count>32||prev.c<3||prev.c>64 ? 6 : 7);""")
    if footprint:
        key='            Cmd& prev = cur_->cmds.back();'
        once('extern "C" void sep_strip_reason(unsigned);','extern "C" void sep_strip_reason(unsigned);\nextern "C" void sep_footprint(unsigned);')
        once(key,key+"""
            if(ep && prim==6 && prev.a==6 && prev.b==start && indices && prev.c>=3 && count>=3 && (prev.d==1||prev.d==2)){
              unsigned mask=0;
              if(recording_visibility_ || !s.rs[kRsZEnable] || (s.vs_handle&15)==4 ||
                 s.rs[kRsFillMode]==0x1b00 || s.rs[kRsFillMode]==0x1b01)mask|=1;
              for(uint32_t texture:s.textures)if(texture){
                uint32_t td=kernel::R32(texture+4)&0x7fffffff;
                if(td==(s.rt.data&0x7fffffff)||td==(s.zs.data&0x7fffffff))mask|=2;
              }
              const uint8_t *prev_ix=prev.d==2 ? cur_->index_snapshots.at(prev.size)->bytes.data() : cur_->bytes.data()+prev.data;
              auto span=[](const uint8_t *p,unsigned n){
                unsigned lo=65535,hi=0;
                for(unsigned j=0;j<n;j++){uint16_t v;std::memcpy(&v,p+2*j,2);lo=std::min(lo,unsigned(v));hi=std::max(hi,unsigned(v));}
                return std::pair<unsigned,unsigned>{lo,hi};};
              auto a=span(prev_ix,prev.c), b=span(indices,count);
              if(a.first>b.second+1 || b.first>a.second+1)mask|=4;
              if(a.second-a.first+1>2ull*prev.c+64 || b.second-b.first+1>2ull*count+64)mask|=8;
              sep_footprint(mask);
            }""")
    return s
