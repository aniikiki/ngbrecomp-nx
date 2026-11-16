    using Part=std::pair<unsigned,unsigned>;
    using Recipe=std::array<std::vector<unsigned char>,6>;
    using Key=std::pair<Part,unsigned>;
    std::map<Key,Recipe> recipes_prev_,recipes_now_;
    std::map<Part,unsigned> occurrences_;
    unsigned obs_f_=0;
    void RecipeObserve(const State&s,unsigned prim,unsigned start,unsigned count,const uint8_t* inds){
        if(obs_f_!=recipe_frame){
            if(obs_f_)for(unsigned k=0;k<65;k++)if(hist_[k])std::fprintf(stderr,"[MODEL_RECIPE] %u %u %u\n",obs_f_,k,hist_[k]);
            memset(hist_,0,sizeof(hist_));
            recipes_prev_.swap(recipes_now_);recipes_now_.clear();occurrences_.clear();
            if(recipe_frame!=obs_f_+1)recipes_prev_.clear();
            obs_f_=recipe_frame;
        }
        Part part={recipe_pc,recipe_key}; Key key={part,occurrences_[part]++};
        auto& r=recipes_now_[key];
        auto add=[&](unsigned i,const void* p,size_t n){auto b=(const unsigned char*)p;if(n)r[i].insert(r[i].end(),b,b+n);};
        auto put=[&](unsigned i,const auto& v){add(i,&v,sizeof v);};
        put(0,s.transforms[256]);put(1,prim);put(1,start);put(1,count);
        put(1,s.index_buffer);put(1,s.index_data);put(1,s.base_vertex);
        for(auto& st:s.streams){put(1,st.vb);put(1,st.stride);}
        if(inds)add(1,inds,2ull*count);
        put(2,s.textures);put(2,s.palettes);put(2,s.vs_handle);
        auto vs=(uintptr_t)s.vs.get(),ps=(uintptr_t)s.ps.get();put(2,vs);put(2,ps);
        put(3,s.rs);put(3,s.tss);put(3,s.simple);
        put(4,s.material);put(4,s.lights);put(4,s.light_enable);
        put(5,s.transforms[2]);put(5,s.transforms[3]);
        unsigned cost_group=2;unsigned bits=0;auto it=recipes_prev_.find(key);
        if(it!=recipes_prev_.end())for(unsigned i=0;i<6;i++)if(it->second[i]==r[i])bits|=1u<<i;
        if(it!=recipes_prev_.end() && (bits&22)==22 && recipe_state_detail_){
            auto& a=it->second[3]; auto& b=r[3]; if(a.size()!=b.size() || (a.size()%4))std::abort();
            std::vector<unsigned> changed;
            for(unsigned j=0;j<b.size();j+=4)if(std::memcmp(a.data()+j,b.data()+j,4))changed.push_back(j/4);
            if(recipe_frame<=30){for(unsigned j:changed)++rank_[j];}
            else{
                if(!ranked_){std::vector<std::pair<unsigned,unsigned>> v;
                    for(auto [j,n]:rank_)v.push_back({n,j});
                    std::sort(v.rbegin(),v.rend());
                    for(unsigned i=0;i<v.size();i++){order_[v[i].second]=i+1;
                        if(i<16)std::fprintf(stderr,"[RECIPE_FIELD] %u %u %u\n",i+1,v[i].second,v[i].first);}
                    ranked_=true;}
                unsigned need=0;for(auto j:changed){auto q=order_.find(j);need=std::max(need,q==order_.end()?9999u:q->second);}
                cost_group=need<=4?0:1;
                if(recipe_setters_ && recipe_frame>30){unsigned group=need<=4?0:1;
                    auto &v=setter_totals_[group];++v[0];for(unsigned i=0;i<9;i++)v[i+1]+=recipe_calls[i];
                    if(recipe_frame==120){for(unsigned g=0;g<2;g++){std::fprintf(stderr,"[RECIPE_SETTERS] %u",g);for(auto n:setter_totals_[g])std::fprintf(stderr," %u",n);std::fprintf(stderr,"\n");}}
                }
                ++budget_[std::min(need,17u)];
                if(recipe_frame==120 || (obs_f_!=last_report_)){last_report_=obs_f_;
                    std::fprintf(stderr,"[RECIPE_DETAIL] %u",obs_f_);for(auto n:budget_)std::fprintf(stderr," %u",n);std::fprintf(stderr,"\n");}
            }
        }
        unsigned bin=it==recipes_prev_.end()?64:bits;
        if(recipe_clock_ && recipe_frame>30){
            auto &v=pre_draw_[cost_group]; ++v[0];
            if(pre_elapsed_){++v[1];v[2]+=pre_elapsed_;}
            if(recipe_frame==120)for(unsigned g=0;g<3;g++)std::fprintf(stderr,"[RECIPE_PRE] %u %llu %llu %llu\n",g,pre_draw_[g][0],pre_draw_[g][1],pre_draw_[g][2]);
        }
        ++hist_[bin];if(obs_f_==120)std::fprintf(stderr,"[MODEL_RECIPE] 120 %u 1\n",bin);
    }
    unsigned hist_[65]={};
    const bool recipe_state_detail_=std::getenv("NGB_RECIPE_FIELDS")!=nullptr;
    bool ranked_=false;
    unsigned last_report_=0,budget_[18]={};
    std::map<unsigned,unsigned> rank_,order_;
    const bool recipe_setters_=std::getenv("NGB_RECIPE_SETTERS")!=nullptr;
    unsigned setter_totals_[2][10]={};
    bool recipe_clock_=std::getenv("NGB_RECIPE_CLOCK")!=nullptr;
    unsigned long long pre_elapsed_=0,pre_draw_[3][3]={};
