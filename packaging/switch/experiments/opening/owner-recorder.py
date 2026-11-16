"""The guest owns the open recorder batch, including replies to FIFO progress
reads. An idle render thread requests publication; never accesses cur_.
Completed immutable batches are still transferred and fenced under m_."""
from pathlib import Path
def transform(s):
 def once(a,b):
  nonlocal s
  assert s.count(a)==1,a
  s=s.replace(a,b)
 # All direct-driver backend calls are made on the same cooperative guest
 # host thread. If it parks on the guest's MMIO progress read, TitleWaits
 # must publish immediately even with no new Draw. Keep that hook intact.
 once('    std::recursive_mutex cap_;', '''    struct GuestOnly {
        void lock() {}
        void unlock() {}
        bool try_lock() {return true;}
    } cap_;
    std::atomic<bool> idle_request_{false};''')
 once('''                    if (cap_.try_lock()) {
                        if (g_pace_on && !cur_->cmds.empty()) g_pace.idle_submit++;
                        Release();
                        cap_.unlock();
                    } else if (g_pace_on) {
                        g_pace.idle_busy++;
                    }''','''                    idle_request_.store(true,std::memory_order_release);''')
 once('        if (!thread_ || cur_->cmds.size() >= kBatchCommands) Submit();','''        if (!thread_ || cur_->cmds.size() >= kBatchCommands ||
            (idle_request_.load(std::memory_order_relaxed) &&
             idle_request_.exchange(false,std::memory_order_acq_rel))) Submit();''')
 # The former idle consumer also retired unreferenced DMA after the last
 # batch. Only enable for trials with the direct progress read hook.
 once('        title_ = std::this_thread::get_id();','')
 return s
