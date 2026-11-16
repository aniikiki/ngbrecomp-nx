"""Share a conservative writer generation for the four PS-only simple ranges."""
def once(s,k,v):
 assert s.count(k)==1,k
 return s.replace(k,v)

def hle(s):
 k='gpu::State g_state;'
 s=once(s,k,k+'''
// The recorder observes the same producer thread. Zero permanently disables reuse on wrap.
static uint64_t ps_epoch=1;
static inline void ps_written(){if(ps_epoch)++ps_epoch;}
extern "C" uint64_t opening_ps_epoch(const void* state){
 return state==&g_state?ps_epoch:0;
}
''')
 # The XDK encode-table import only writes 0x300..0x3fc or 0x1d78,
 # disjoint from the four observed ranges. All other possible writers invalidate.
 assert s.count('if ((method >= 0x300 && method < 0x400) || method == 0x1D78)')==1
 k='g_state.simple[(c.r[ECX] & 0x1FFC) >> 2] = c.r[EDX];'
 s=once(s,k,'''{unsigned m=c.r[ECX]&0x1ffc;
 if((m>=0x260 && m<=0x28c)||(m>=0xa60 && m<=0xadc)||m==0x17f8||(m>=0x1e20 && m<=0x1e78))ps_written();}
        '''+k)
 for k in ('const uint32_t* d = ps->def;', 'uint32_t reg = c.r[ECX], src = c.a(0), n = c.r[EAX];'):
    s=once(s,k,'ps_written(); '+k)
 k='g_state = gpu::State{};';assert s.count(k)==2
 return s.replace(k,'ps_written(); '+k)

def recorder(s):
 s='extern "C" __UINT64_TYPE__ opening_ps_epoch(const void*);\n'+s
 k='    State sent_;'
 s=once(s,k,'''    uint64_t last_ps_epoch_=0;
    bool can_reuse_ps_=false;
'''+k)
 k='        SendFixedRanges(now,'
 s=once(s,k,'''        const auto gen=opening_ps_epoch(&s);
        can_reuse_ps_=gen && gen==last_ps_epoch_;
        last_ps_epoch_=gen;
'''+k)
 k='        if (!std::memcmp(previous, now + r.off, r.len)) return;'
 return once(s,k,'''        if constexpr(I==0 || I==2 || I==3 || I==5){
            if(can_reuse_ps_){
                static const bool verify=std::getenv("NGB_PS_RANGE_VERIFY")!=nullptr;
                if(verify){
                    if(std::memcmp(previous,now+r.off,r.len))std::abort();
                    static thread_local unsigned count;
                    if((++count % 4096)==0)std::fprintf(stderr,"[PS_RANGE_CHECK] %zu %u\\n",I,count);
                }
                return;
            }
        }
'''+k)
