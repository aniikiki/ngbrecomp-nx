// Only the diagnostic build includes this recorder. Integrate the union of
// intervals once at each edge, including intervals crossing a FIFO flip.
namespace {
struct PipeSlice { uint64_t wait{}, create{}, both{}; unsigned starts{}, ends{}, calls{}; };
struct PipeTimeline {
    PipeSlice bins[121]{};
    unsigned frame=0, waiting=0, creating=0, bad=0, tables=0;
    uint64_t last=0;
    void advance(uint64_t t) {
        if(t<last) { ++bad; return; }
        if(frame && frame<=120) {
            auto& b=bins[frame];auto dt=t-last;
            if(waiting)b.wait+=dt;
            if(creating)b.create+=dt;
            if(waiting&&creating)b.both+=dt;
        }
        last=t;
    }
    void event(uint64_t t,bool pipe,bool enter) {
        advance(t);auto& depth=pipe?creating:waiting;
        if(enter)++depth;else if(depth)--depth;else ++bad;
        if(frame && frame<=120){
            auto& b=bins[frame]; if(pipe){if(enter)++b.starts;else ++b.ends;}
            else if(enter)++b.calls;
        }
    }
    void flip(uint64_t t,unsigned f){advance(t);frame=f+1;}
};
}
