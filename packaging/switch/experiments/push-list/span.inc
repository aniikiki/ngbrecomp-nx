// Parse the current words every time. The common one-chunk strip points
// straight into the guest's allocation. Only disjoint chunks need stitching.
static bool SpanPush(uint32_t data,uint32_t size){
    if(size<12 || size>65536 || (size&3) || data<0x84000000u || data>0x88000000u-size)return false;
    auto src=PushSpan(data,size);if(!src)return false;
    auto get=[&](unsigned i){uint32_t v;std::memcpy(&v,src+4*i,4);return v;};
    unsigned n=size/4,h=get(0),prim=get(1);
    if((h&0xe0000003u)||((h>>18)&2047)!=1||(h&0x1ffc)!=0x17fc||!prim)return false;
    struct Chunk{unsigned first,count;bool wide;};Chunk chunks[32];unsigned num=0,total=0,pos=2;
    for(;pos<n;){h=get(pos++);unsigned m=h&0x1ffc,c=(h>>18)&2047;
        if((h&0xe0000003)==0x20000000 || (h&3)==1)break;
        if((h&3)||!c||c>n-pos)return false;
        if(m==0x17fc){
            if(c!=1||get(pos)!=0)return false;
            if(++pos<n && (get(pos)&0xe0000003)!=0x20000000 && (get(pos)&3)!=1)return false;
            break;
        }
        if(num==32 || (m!=0x1800 && m!=0x1808))return false;
        chunks[num++]={pos,c,m==0x1808};total+=c*(m==0x1800?2:1);pos+=c;
    }
    if(!num)return false;
    if(num==1 && !chunks[0].wide)Draw(prim,0,total,src+4*chunks[0].first);
    else{static thread_local std::vector<uint16_t> joined;joined.resize(total);unsigned at=0;
        for(unsigned i=0;i<num;i++){auto c=chunks[i];if(c.wide){for(unsigned j=0;j<c.count;j++)joined[at++]=uint16_t(get(c.first+j));}
            else{std::memcpy(joined.data()+at,src+4*c.first,c.count*4);at+=c.count*2;}}
        Draw(prim,0,total,reinterpret_cast<const uint8_t*>(joined.data()));
    }
    return true;
}
