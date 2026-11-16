"""Warm selectable shader cache. Only LoadVertexShader writes g_program during
play; compare once at that writer. During a stable generation a selection
uses object identity and address, without scanning the microcode or allocating.
After any change use the old program bytes to prove equality before reuse."""
def transform(s):
 def replace(k,v):
  nonlocal s
  assert s.count(k)==1,k
  s=s.replace(k,v)
 k='uint32_t g_program[136][4];'
 replace(k,k+'''
struct BankChoice {
 uint64_t epoch=0; uint32_t handle=0, start=0;
 std::shared_ptr<gpu::VertexShader> decl, program;
};
static BankChoice bank_choices[64][4];
static unsigned bank_rotor[64];
static uint64_t bank_epoch=1;
static void invalidate_bank() {
 if (++bank_epoch==0) {
  for(auto& set:bank_choices)for(auto& v:set)v={};
  bank_epoch=1;
 }
}
''')
 k='''        if (it != g_vs.end())
            for (size_t i = 0; i < it->second->program.size() / 4 && at + i < 136; i++)
                std::memcpy(g_program[at + i], &it->second->program[i * 4], 16);'''
 replace(k,'''        if(it!=g_vs.end() && at<136){
            size_t len=std::min<size_t>(136-at,it->second->program.size()/4)*16;
            if(len && std::memcmp(&g_program[at],it->second->program.data(),len)){
                std::memcpy(&g_program[at],it->second->program.data(),len);
                invalidate_bank();
            }
        }''')
 k='''        auto vs = std::make_shared<gpu::VertexShader>();
        auto it = g_vs.find(h);'''
 replace(k,'''        auto it=g_vs.find(h);
        auto* decl=it==g_vs.end()?nullptr:it->second.get();
        unsigned set=((h>>2)^at^(h>>11))&63;
        BankChoice* slot=nullptr; bool reused=false;
        for(auto& e:bank_choices[set]){
            if(!e.program){if(!slot)slot=&e;continue;}
            if(e.handle!=h || e.start!=at || e.decl.get()!=decl)continue;
            const auto& code=e.program->program;
            if(e.epoch==bank_epoch ||
               (at>=136 ? code.empty() : !code.empty() && code.size()<=(136-at)*4 &&
                !std::memcmp(&g_program[at],code.data(),code.size()*4))){
                e.epoch=bank_epoch;reused=true;
                g_selected=e.program;g_state.vs_handle=h|1;g_state.vs=g_selected;
                break;
            }
        }
        if(reused)break;
        auto vs=std::make_shared<gpu::VertexShader>();''')
 replace('        g_selected = vs;', '''        if(!slot)slot=&bank_choices[set][bank_rotor[set]++&3];
        *slot={bank_epoch,h,at,it==g_vs.end()?nullptr:it->second,vs};
        g_selected = vs;''')
 replace('    g_selected.reset();','    for(auto& set:bank_choices)for(auto& v:set)v={};\n    bank_epoch=1;\n    g_selected.reset();')
 return s
