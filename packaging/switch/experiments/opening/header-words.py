"""Capture exactly 12 or 20 header bytes; compare register-sized values before materializing a record."""
helper='''static inline bool changed_header(HeaderCopy& out,const HeaderCopy& prev,const void* ptr,bool wide) {
    const auto *p=static_cast<const uint8_t*>(ptr);
    uint64_t a,b=0,x,y; uint32_t c,z;
    std::memcpy(&a,p,8); std::memcpy(&c,p+8,4);
    if(wide) std::memcpy(&b,p+12,8);
    std::memcpy(&x,prev.w,8); std::memcpy(&z,prev.w+2,4); std::memcpy(&y,prev.w+3,8);
    if(!((a^x)|(b^y)|(c^z))) return false;
    std::memcpy(out.w,&a,8);out.w[2]=c;std::memcpy(out.w+3,&b,8);
    return true;
}'''
def transform(t):
 a='    void SendHeader(uint32_t header)';b='std::memcpy(now.w, kernel::HostPtr(header), type < 0x20000 || type == 0x30000 ? 12 : 20);'
 c='if (!std::memcmp(r.copy->w, now.w, sizeof now.w)) return;'
 assert all(t.count(k)==1 for k in (a,b,c))
 return t.replace(a,helper+'\n'+a).replace(b,'const void* src=kernel::HostPtr(header);').replace(c,'if (!changed_header(now,*r.copy,src,type>=0x20000 && type!=0x30000)) return;')
