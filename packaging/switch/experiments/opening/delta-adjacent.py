"""Extend the last wire record only for consecutive destination offsets within one State command."""
def transform(s):
    a='    void WriteDelta(size_t off, const uint8_t* now, size_t bytes) {'
    b='        size_t first = cur_->bytes.size();'
    k='        const uint32_t head[] = {uint32_t(off), uint32_t(bytes)};'
    assert all(s.count(i)==1 for i in (a,b,k))
    return s.replace(a,'    size_t delta_header_=0,delta_end_=0;\n'+a).replace(b,b+'\n        delta_end_=0;').replace(k,'''        if(delta_end_ && off==delta_end_) {
            size_t at=cur_->bytes.size();
            cur_->bytes.resize(at+bytes);
            uint8_t* data=cur_->bytes.data();
            uint32_t total=uint32_t(at+bytes-delta_header_-8);
            std::memcpy(data+delta_header_+4,&total,4);
            std::memcpy(data+at,now+off,bytes);
            delta_end_=off+bytes;
            return;
        }
        delta_header_=cur_->bytes.size();delta_end_=off+bytes;
'''+k)
