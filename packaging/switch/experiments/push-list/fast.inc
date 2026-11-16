// Fast path for exactly one complete indexed primitive. Validate the command
// grammar on admission. Verify its bytes on every reuse (buffers are mutable).
// Unknown methods, jumps, multiple draws and truncated commands stay original.
static bool CachedPush(uint32_t data, uint32_t size) {
    struct Slot { uint32_t address=0, primitive=0; std::vector<uint32_t> raw; std::vector<uint16_t> index; };
    static Slot slots[512];
    if (size<20 || size>65536 || (size&3u) || data<0x84000000u || data>0x88000000u-size) return false;
    // Only direct physical RAM pages. Do not trigger an MMIO or render target read.
    extern const uint8_t* PushSpan(uint32_t,uint32_t);
    const uint8_t* src=PushSpan(data,size);
    if(!src)return false;
    auto& slot=slots[((data>>4)^(data>>13))&511];
    uint32_t tail;std::memcpy(&tail,src+size-4,4);
    unsigned valid_size=((tail&3)==1 || (tail&0xe0000003u)==0x20000000u)?size-4:size;
    if(slot.address!=data || slot.raw.size()!=valid_size/4 || std::memcmp(src,slot.raw.data(),valid_size)){
        auto get=[&](size_t i){ uint32_t v;std::memcpy(&v,src+4*i,4);return v; };
        unsigned n=valid_size/4;
        if((get(0)&0xe0000003u) || (get(0)&0x1ffcu)!=0x17fc || ((get(0)>>18)&2047)!=1 || !get(1))return false;
        unsigned pos=2,total=0;
        while(pos<n){uint32_t h=get(pos),count=(h>>18)&2047,m=h&0x1ffc;
            if(m==0x17fc)break;
            if((h&0xe0000003u)==0x20000000u || (h&3u) || !count || count>n-pos-1 || (m!=0x1800 && m!=0x1808))return false;
            total+=count*(m==0x1800?2:1);pos+=1+count;
        }
        if(!total || (pos!=n && (pos+2!=n||(get(pos)&0xe0000003u)||(get(pos)&0x1ffcu)!=0x17fc||((get(pos)>>18)&2047)!=1||get(pos+1))))return false;
        slot.address=data;slot.raw.resize(n);std::memcpy(slot.raw.data(),src,valid_size);
        slot.primitive=get(1);slot.index.resize(total);
        for(unsigned i=2,at=0;i<pos;){uint32_t h=get(i++),cnt=(h>>18)&2047;
            if((h&0x1ffc)==0x1800){std::memcpy(slot.index.data()+at,src+4*i,4*cnt);at+=2*cnt;}
            else for(unsigned j=0;j<cnt;j++)slot.index[at++]=uint16_t(get(i+j));
            i+=cnt;
        }
    }
    Draw(slot.primitive,0,slot.index.size(),reinterpret_cast<const uint8_t*>(slot.index.data()));
    return true;
}
