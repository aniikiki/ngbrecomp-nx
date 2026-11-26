"""Append changed header records directly to their owning batch."""
def transform(t):
    # Current recorders already retain headers in ordered groups in each batch.
    if 'std::vector<HeaderGroup> header_groups;' in t:
        return t
    def rep(old,new,n=1):
        nonlocal t
        assert t.count(old)==n,old
        t=t.replace(old,new)
    rep('struct Batch {','struct Batch {\n    std::vector<HeaderSend> header_records;\n    size_t header_first=0;')
    rep('pending_headers_.push_back(h);','cur_->header_records.push_back(h);',2)
    rep('if (pending_headers_.empty()) return;', 'if (cur_->header_records.size()==cur_->header_first) return;')
    rep('c.data = Put(pending_headers_.data(), pending_headers_.size() * sizeof(pending_headers_[0]));','c.a = uint32_t(cur_->header_first);')
    rep('c.size = uint32_t(pending_headers_.size());','c.size = uint32_t(cur_->header_records.size()-cur_->header_first);')
    rep('pending_headers_.clear();','cur_->header_first=cur_->header_records.size();')
    rep('    std::vector<HeaderSend> pending_headers_;','')
    rep('        b->cmds.clear();','        b->header_records.clear();\n        b->header_first=0;\n        b->cmds.clear();')
    rep('                    HeaderSend h;\n                    std::memcpy(&h, data + i * sizeof h, sizeof h);','                    const HeaderSend& h = b.header_records[c.a+i];')
    return t
