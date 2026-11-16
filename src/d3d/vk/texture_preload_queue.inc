// The file thread copies only the intersection with a known static texture.
// No guest pointers cross threads. Incomplete/out-of-order reads fall back to first use.
struct Slice {uint32_t pos,n,fmt;};
struct Pack {const char* name; unsigned first,count;};
#include "texture_index.inc"
struct WarmJob {const Slice* rec;std::vector<uint8_t> bytes;unsigned filled;};
static std::mutex warm_mu;
static std::map<const Slice*,WarmJob> assembling;
static std::deque<WarmJob> jobs;
static size_t queued_bytes;
static bool tex_enabled(){
    static const bool enabled=[]{
#ifdef __SWITCH__
        return access("sdmc:/switch/ngb-runtime/disable-texture-preload.flag",F_OK)!=0;
#else
        return !std::getenv("NGB_DISABLE_TEXTURE_PRELOAD");
#endif
    }();
    return enabled;
}
extern "C" void ngb_texture_read(const char* name,uint64_t pos,const uint8_t* data,unsigned n){
    if(!n || !tex_enabled())return;
    auto p=std::lower_bound(std::begin(packs),std::end(packs),name,[](const Pack& a,const char* b){return strcasecmp(a.name,b)<0;});
    if(p==std::end(packs)||strcasecmp(p->name,name))return;
    const Slice* end=slices+p->first+p->count;
    auto r=std::lower_bound(slices+p->first,end,pos>524288?pos-524288:0,[](const Slice& a,uint64_t b){return a.pos<b;});
    std::lock_guard lock(warm_mu);
    for(;r!=end && r->pos<pos+n;++r){
        uint64_t a=std::max<uint64_t>(r->pos,pos),b=std::min<uint64_t>(uint64_t(r->pos)+r->n,pos+n);
        if(a>=b)continue;
        auto i=assembling.find(r);
        if(i==assembling.end()){
            if(a!=r->pos)continue;
            while(!jobs.empty() && queued_bytes+r->n>(12u<<20)){
                queued_bytes-=jobs.front().bytes.size();jobs.pop_front();
            }
            if(assembling.size()>=32){auto old=assembling.begin();queued_bytes-=old->second.bytes.size();assembling.erase(old);}
            if(queued_bytes+r->n>(12u<<20))continue;
            i=assembling.emplace(r,WarmJob{r,std::vector<uint8_t>(r->n),0}).first;queued_bytes+=r->n;
        }
        auto& j=i->second;
        if(a==r->pos)j.filled=0;
        if(a-r->pos>j.filled)continue;
        std::memcpy(j.bytes.data()+(a-r->pos),data+(a-pos),b-a);
        j.filled=std::max(j.filled,unsigned(b-r->pos));
        if(j.filled==r->n){jobs.push_back(std::move(j));assembling.erase(i);}
    }
}
