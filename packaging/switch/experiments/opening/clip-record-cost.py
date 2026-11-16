"""Carry sampled producer cost to the actual consumer cull decision, in command order."""
def recorder(s):
 def one(a,b):
  nonlocal s
  assert s.count(a)==1,a
  s=s.replace(a,b)
 s='#include <time.h>\nextern "C" {thread_local bool ngb_actual_clip;}\n'+s
 k='        SendState(s, start + count);'
 one(k,'''        static unsigned rng=1347; rng=rng*1664525u+1013904223u;
        unsigned sample=rng>>29;uint64_t began=0,blank=0;
        auto cpu=[]()->uint64_t{timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))std::abort();return uint64_t(t.tv_sec)*1000000000+t.tv_nsec;};
        if(sample==0)began=cpu();else if(sample==1){auto t=cpu();blank=cpu()-t;}
'''+k)
 k='        cur_->cmds.push_back(c);\n        if (!thread_ || cur_->cmds.size() >= kBatchCommands) Submit();'
 one(k,'''        c.f=!sample?float(cpu()-began+1):sample==1?-float(blank+1):0;
'''+k)
 k='            case Op::Draw:'
 one(k,k+'\n                ngb_actual_clip=false;')
 for k in ('inner_->Draw(state_, c.a, c.b, c.c, snapshot.bytes.data(), &snapshot.bounds);','inner_->Draw(state_, c.a, c.b, c.c, c.d ? data : nullptr);'):
  one(k,k+' account_clip(c);')
 k='                inner_->Present(c.s1);'
 one(k,k+r'''
                if(++record_frames_==30 || record_frames_==120){
                    for(unsigned i=0;i<2;i++){auto &x=record_cost_[i];std::fprintf(stderr,"[CLIP_RECORD] f=%u cut=%u cmds=%llu n=%llu ns=%llu blanks=%llu blank_ns=%llu\n",record_frames_,i,x[0],x[1],x[2],x[3],x[4]);}
                    std::memset(record_cost_,0,sizeof(record_cost_));
                }''')
 k='    bool thread_;'
 one(k,'''    unsigned record_frames_=0;
    unsigned long long record_cost_[2][5]{};
    void account_clip(const Cmd &c){auto &x=record_cost_[ngb_actual_clip];++x[0];if(c.f>0){++x[1];x[2]+=uint64_t(c.f)-1;}else if(c.f<0){++x[3];x[4]+=uint64_t(-c.f)-1;}}
'''+k)
 return s
def backend(s):
 k='                ++rigid_skipped_;';assert s.count(k)==1
 return 'extern "C" {extern thread_local bool ngb_actual_clip;}\n'+s.replace(k,k+'ngb_actual_clip=true;')
