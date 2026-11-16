"""Give each index slot at most one owner in a batch per immutable snapshot."""
def transform(s):
    def one(a,b):
        nonlocal s
        assert s.count(a)==1,a
        s=s.replace(a,b)
    one('    std::shared_ptr<const IndexSnapshot> snapshot;','''    std::shared_ptr<const IndexSnapshot> snapshot;
    uint64_t owner_batch = 0;
    uint32_t owner_pos = 0;''')
    one('std::shared_ptr<const IndexSnapshot> CaptureIndices(', 'IndexSlot* CaptureIndices(')
    one('            return slot.snapshot;', '            return &slot;')
    one('        slot.snapshot = copy;\n        return copy;', '''        slot.snapshot = std::move(copy);
        slot.owner_batch = 0;
        return &slot;''')
    one('''                c.size = uint32_t(cur_->index_snapshots.size());
                cur_->index_snapshots.push_back(std::move(snapshot));''','''                if (snapshot->owner_batch != cur_->id) {
                    snapshot->owner_pos = uint32_t(cur_->index_snapshots.size());
                    cur_->index_snapshots.push_back(snapshot->snapshot);
                    snapshot->owner_batch = cur_->id;
                }
                c.size = snapshot->owner_pos;''')
    return s
