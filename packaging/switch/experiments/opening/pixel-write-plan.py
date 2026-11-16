"""Prepare constant destinations at immutable shader creation; still apply every required write."""
def transform(s):
 key='std::unordered_map<uint32_t, std::shared_ptr<gpu::PixelShader>> g_ps;'
 assert s.count(key)==1
 s=s.replace(key,'''struct PlannedPixel : gpu::PixelShader {
    uint16_t dest[8][18]{};
    uint8_t len[8]{};
    void prepare(){
        auto bind=[&](uint32_t reg,uint32_t method){if(reg<8)dest[reg][len[reg]++]=uint16_t(method/4);};
        for(unsigned i=0;i<8;i++){
            bind((def[57]>>(4*i))&15,gpu::kMPsConstant0+4*i);
            bind((def[58]>>(4*i))&15,gpu::kMPsConstant1+4*i);
        }
        bind(def[59]&15,gpu::kMPsFinalConstant0);
        bind((def[59]>>4)&15,gpu::kMPsFinalConstant1);
    }
};
const PlannedPixel* active_pixel_plan=nullptr;
std::unordered_map<uint32_t, std::shared_ptr<PlannedPixel>> g_ps;''')
 assert s.count('std::make_shared<gpu::PixelShader>()')==2
 s=s.replace('std::make_shared<gpu::PixelShader>()','std::make_shared<PlannedPixel>()')
 for src in ('def','HostPtr(g_new_decl)'):
    k=f'std::memcpy(ps->def, {src}, sizeof(ps->def));';assert s.count(k)==1;s=s.replace(k,k+' ps->prepare();')
 for k,tail in [('g_state.ps = nullptr;','active_pixel_plan=nullptr;'),('g_state.ps = ps;','active_pixel_plan=ps.get();'),('g_state = gpu::State{};','active_pixel_plan=nullptr;')]:
    assert k in s;s=s.replace(k,k+tail)
 k='gpu::ApplyPixelConstants(g_state, reg, n);';assert s.count(k)==1
 return s.replace(k,'''static const bool control=std::getenv("NGB_PIXEL_PLAN_CONTROL")!=nullptr;
        static const bool check=std::getenv("NGB_PIXEL_PLAN_VERIFY")!=nullptr;
        if(!control && n==1 && reg<8 && active_pixel_plan && g_state.ps.get()==active_pixel_plan){
            auto apply=[&](){
                auto num=active_pixel_plan->len[reg];
                if(!num)return;
                uint32_t packed=gpu::PackColor(g_state.psc[reg]);
                for(unsigned j=0;j<num;j++)g_state.simple[active_pixel_plan->dest[reg][j]]=packed;
            };
            if(check){
                auto input=g_state.simple;gpu::ApplyPixelConstants(g_state,reg,n);
                auto expected=g_state.simple;g_state.simple=input;apply();
                if(expected!=g_state.simple)std::abort();
                static unsigned hits;if(++hits%4096==0)std::fprintf(stderr,"[PIXEL_PLAN_CHECK] %u\\n",hits);
            }else apply();
        }else gpu::ApplyPixelConstants(g_state,reg,n);''')
