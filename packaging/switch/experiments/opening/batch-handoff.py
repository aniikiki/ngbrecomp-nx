"""Hand off recorded commands and reserve a recycled batch under one lock."""
def transform(t):
    k='''        submitted_ = id;
        {
            std::lock_guard lock(m_);
            queue_.push_back(cur_);
        }
        cv_.notify_one();
        cur_ = NewBatch();'''
    assert t.count(k)==1
    return t.replace(k,'''        submitted_ = id;
        Batch* spare = nullptr;
        {
            std::lock_guard lock(m_);
            queue_.push_back(cur_);
            if (!free_.empty()) {
                spare = free_.back();
                free_.pop_back();
            }
        }
        cv_.notify_one();
        // Let the consumer start immediately, even when allocation is needed.
        cur_ = spare ? spare : new Batch;
        cur_->id = ++next_id_;''')
