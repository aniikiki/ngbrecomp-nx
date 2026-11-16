"""Offline experiment: did sampled Vulkan draws produce any passing samples?"""
from pathlib import Path
import json
import subprocess as sp
import shlex
import sys

core=Path('/work/build/switch-runtime/core-perf')
host=core.parent/'host'
cut='--cut-trial' in sys.argv
planes='--planes' in sys.argv
certify='--certify' in sys.argv
helper_name='rigid-planes.inc' if planes else 'rigid-bounds.inc'
bounds='--bounds' in sys.argv
nocull='--compare-cull' in sys.argv
clip='--clip' in sys.argv or nocull or bounds or certify
out=core/('visibility-cut' if cut else 'visibility-bounds' if bounds else 'visibility-cull' if nocull else 'visibility-clip' if clip else 'visibility-work')
if certify: out=core/'clip-certified'
if planes: out=out.with_name(out.name+'-planes')
out.mkdir(exist_ok=True)
cmds=sp.check_output(['ninja','-t','commands','ngb-runtime-test'],cwd=host,text=True).splitlines()
link=json.loads((core/'exact-link.json').read_text())
def object_file(name, src):
    cmd=next(shlex.split(l) for l in cmds if l.endswith('/'+name))
    orig=Path(cmd[-1]); f=out/orig.name; f.write_text(src)
    obj=str(f)+'.o'
    cmd[cmd.index('-o')+1]=obj
    cmd[cmd.index('-MF')+1]=obj+'.d'
    cmd[1:1]=['-I'+str(orig.parent)]
    if certify and name=='vk/backend.cpp':cmd.insert(1,'-DNGB_RIGID_CLIP')
    cmd[-1]=str(f)
    sp.run(cmd,cwd=host,check=True)
    link.insert(1,obj)
src=Path('/work/packaging/switch/runtime/scene/bridge.c').read_text()
tag='    ++scene_flips;'
assert src.count(tag)==1
object_file('scene/bridge.c','unsigned ngb_coverage_frame;\n'+src.replace(tag,tag+' __atomic_store_n(&ngb_coverage_frame,scene_flips,__ATOMIC_RELAXED);'))
src=Path('/work/src/d3d/vk/backend.cpp').read_text()
def replace(tag,val):
    global src
    assert src.count(tag)==1,tag
    src=src.replace(tag,val)
src='extern "C" unsigned ngb_coverage_frame;\n'+src
if cut:
    exec(Path(__file__).with_name('rigid-cut-trial.inc.py').read_text())
    object_file('vk/backend.cpp',src)
    link[link.index('-o')+1]=str(out/'replay')
    sp.run(link,cwd=host,check=True)
    sys.exit(0)
tag='    VkQueryPool vis_pool_[2] = {};'
replace(tag,tag+'''
    struct Cover {unsigned frame,rt,verts,mask,zwrite,sten,blend;};
    std::vector<Cover> coverage_[2];
    unsigned coverage_seq_=0;
''')
replace('qci.queryCount = kVisQueries;', 'qci.queryCount = 2*kVisQueries;')
replace('cmd_, vis_pool_[slot_], 0, kVisQueries);','cmd_, vis_pool_[slot_], 0, 2*kVisQueries);')
tag='    if (!vis_q_[slot].empty()) {'
replace(tag,'''    auto &cover=coverage_[slot];
    if (!cover.empty()){
        std::vector<uint64_t> results(cover.size());
        if(d_.vkGetQueryPoolResults(dev_,vis_pool_[slot],kVisQueries,uint32_t(cover.size()),
              results.size()*8,results.data(),8,VK_QUERY_RESULT_64_BIT|VK_QUERY_RESULT_WAIT_BIT)!=VK_SUCCESS)std::abort();
        for(size_t i=0;i<cover.size();i++){
            auto c=cover[i];
            std::fprintf(stderr,"[COVER] %u %08x %u %u %u %u %u %llu\\n",c.frame,c.rt,c.verts,c.mask,c.zwrite,c.sten,c.blend,(unsigned long long)results[i]);
        }
        cover.clear();
    }
'''+tag)
tag='    if (visq != ~0u) d_.vkCmdEndQuery(cmd_, vis_pool_[slot_], visq);'
a=src.index('    if (a.index_count) {',src.index('    uint32_t visq = ~0u;'))
src=src[:a]+'''    unsigned f=__atomic_load_n(&ngb_coverage_frame,__ATOMIC_RELAXED);
    if(f>=1800 && f<1916 && !vis_on_ && vis_pool_[slot_] &&
       (++coverage_seq_%7)==0 && coverage_[slot_].size()<kVisQueries){
        visq=kVisQueries+uint32_t(coverage_[slot_].size());
        coverage_[slot_].push_back({f,s.rt.data,count,(unsigned)k.wmask,(unsigned)k.zwrite,(unsigned)k.sten,(unsigned)k.blend});
        d_.vkCmdBeginQuery(cmd_,vis_pool_[slot_],visq,0);
    }
'''+src[a:]
assert tag in src
if clip:
    # The standalone host device explicitly enables this feature. Reject a
    # shared device because we do not control which features it enabled.
    tag='vkGetPhysicalDeviceFeatures(phys_, &have);'
    replace(tag,tag+' if(!have.pipelineStatisticsQuery)std::abort(); f2.features.pipelineStatisticsQuery=VK_TRUE;')
    tag='    unsigned coverage_seq_=0;'
    replace(tag,tag+' VkQueryPool clip_pool_[2]={};')
    tag='    qci.queryCount = 2*kVisQueries;'
    replace(tag,tag+'''
    if(shared_)std::abort();
    VkQueryPoolCreateInfo qc{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};
    qc.queryType=VK_QUERY_TYPE_PIPELINE_STATISTICS;
    qc.queryCount=kVisQueries;
    qc.pipelineStatistics=VK_QUERY_PIPELINE_STATISTIC_INPUT_ASSEMBLY_PRIMITIVES_BIT|
       VK_QUERY_PIPELINE_STATISTIC_VERTEX_SHADER_INVOCATIONS_BIT|
       VK_QUERY_PIPELINE_STATISTIC_CLIPPING_INVOCATIONS_BIT|
       VK_QUERY_PIPELINE_STATISTIC_CLIPPING_PRIMITIVES_BIT|
       VK_QUERY_PIPELINE_STATISTIC_FRAGMENT_SHADER_INVOCATIONS_BIT;
    for(auto &pool:clip_pool_)if(d_.vkCreateQueryPool(dev_,&qc,nullptr,&pool)!=VK_SUCCESS)std::abort();''')
    tag='if (vis_pool_[i]) d_.vkDestroyQueryPool'
    replace(tag,'if(clip_pool_[i])d_.vkDestroyQueryPool(dev_,clip_pool_[i],nullptr);\n            '+tag)
    tag='if (vis_pool_[slot_]) d_.vkCmdResetQueryPool'
    replace(tag,'d_.vkCmdResetQueryPool(cmd_,clip_pool_[slot_],0,kVisQueries);\n    '+tag)
    tag='d_.vkCmdBeginQuery(cmd_,vis_pool_[slot_],visq,0);'
    replace(tag,tag+' d_.vkCmdBeginQuery(cmd_,clip_pool_[slot_],visq-kVisQueries,0);')
    tag='    if (visq != ~0u) d_.vkCmdEndQuery(cmd_, vis_pool_[slot_], visq);'
    replace(tag,'    if(visq!=~0u && visq>=kVisQueries)d_.vkCmdEndQuery(cmd_,clip_pool_[slot_],visq-kVisQueries);\n'+tag)
    tag='        for(size_t i=0;i<cover.size();i++){'
    replace(tag,'''        std::vector<std::array<uint64_t,5>> stats(cover.size());
        if(d_.vkGetQueryPoolResults(dev_,clip_pool_[slot],0,uint32_t(stats.size()),stats.size()*40,stats.data(),40,
            VK_QUERY_RESULT_64_BIT|VK_QUERY_RESULT_WAIT_BIT)!=VK_SUCCESS)std::abort();
'''+tag+'''
            const auto &v=stats[i];std::fprintf(stderr,"[CLIP] %u %08x %llu %llu %llu %llu %llu %llu\\n",cover[i].frame,cover[i].rt,
                (unsigned long long)results[i],(unsigned long long)v[0],(unsigned long long)v[1],(unsigned long long)v[2],(unsigned long long)v[3],(unsigned long long)v[4]);''')
if nocull:
    replace('unsigned frame,rt,verts,mask,zwrite,sten,blend;', 'unsigned frame,rt,verts,mask,zwrite,sten,blend,vs,program,pre;')
    replace('(unsigned)k.sten,(unsigned)k.blend});', '(unsigned)k.sten,(unsigned)k.blend,s.vs_handle,(unsigned)prog,(unsigned)a.pretransformed});')
    replace('qc.queryCount=kVisQueries;', 'qc.queryCount=2*kVisQueries;')
    replace('clip_pool_[slot_],0,kVisQueries);','clip_pool_[slot_],0,2*kVisQueries);')
    tag='    if (visq != ~0u) d_.vkCmdEndQuery(cmd_, vis_pool_[slot_], visq);'
    replace(tag,tag+'''
    if(visq!=~0u && visq>=kVisQueries){
        auto dry=k;
        dry.cull=0;dry.wmask=0;dry.zen=0;dry.zwrite=0;dry.sten=0;
        VkPipeline probe=Pipeline(dry);if(!probe)std::abort();
        BindPipeline(probe);
        d_.vkCmdBeginQuery(cmd_,clip_pool_[slot_],visq,0);
        if(a.index_count)d_.vkCmdDrawIndexed(cmd_,a.index_count,1,0,a.base_vertex,0);
        else d_.vkCmdDraw(cmd_,a.draw_count,1,0,0);
        d_.vkCmdEndQuery(cmd_,clip_pool_[slot_],visq);
        BindPipeline(pipe);
    }
''')
    tag='        for(size_t i=0;i<cover.size();i++){'
    replace(tag,'''        std::vector<std::array<uint64_t,5>> dry(cover.size());
        if(d_.vkGetQueryPoolResults(dev_,clip_pool_[slot],kVisQueries,uint32_t(dry.size()),dry.size()*40,dry.data(),40,
            VK_QUERY_RESULT_64_BIT|VK_QUERY_RESULT_WAIT_BIT)!=VK_SUCCESS)std::abort();
'''+tag+'''
            std::fprintf(stderr,"[DRY] %u %08x %llu %llu %llu %llu %08x %u %u\\n",cover[i].frame,cover[i].rt,
                (unsigned long long)results[i],(unsigned long long)stats[i][3],(unsigned long long)dry[i][3],(unsigned long long)dry[i][4],cover[i].vs,cover[i].program,cover[i].pre);''')
if bounds:
    tag='void VulkanBackend::VisibilityEnd('
    replace(tag,Path(__file__).with_name(helper_name).read_text()+'\n'+tag)
    replace('unsigned frame,rt,verts,mask,zwrite,sten,blend;', 'unsigned frame,rt,verts,mask,zwrite,sten,blend,pred;')
    replace('(unsigned)k.sten,(unsigned)k.blend});','''(unsigned)k.sten,(unsigned)k.blend,
           (!prog && !a.pretransformed && !s.rs[kRsVertexBlend] &&
            (s.vs_handle==0x142 || s.vs_handle==0x152 || s.vs_handle==0x112))?RigidBoundsPrediction(a,c.wvp):0});''')
    tag='            const auto &v=stats[i];'
    replace(tag,'            std::fprintf(stderr,"[BOUND] %u %u %llu %llu\\n",cover[i].frame,cover[i].pred,(unsigned long long)results[i],(unsigned long long)stats[i][3]);\n'+tag)
if certify:
    # Run the original draw on every production-positive decision in this
    # window, testing the actual release predicate rather than a second copy.
    replace('    if (!pk_given_) CapturePeek(s, pk_);\n    st_.draws++;',
            '    bool predicted_out=false;\n    if (!pk_given_) CapturePeek(s, pk_);\n    st_.draws++;')
    replace('                ++rigid_skipped_;\n                return;',
            '                ++rigid_skipped_;predicted_out=true;')
    replace('(++coverage_seq_%7)==0','predicted_out')
    replace('if(f>=1800 && f<1916','if(f>=1800 && f<1916 && predicted_out && coverage_[slot_].size()>=kVisQueries)std::abort();\n    if(f>=1800 && f<1916')
    replace('    unsigned coverage_seq_=0;', '    unsigned coverage_seq_=0; bool certificate_announced_=false;')
    tag='    unsigned f=__atomic_load_n(&ngb_coverage_frame,__ATOMIC_RELAXED);'
    replace(tag,tag+' if(!certificate_announced_){std::fprintf(stderr,"[CERTIFY] all release-positive submissions\\n");certificate_announced_=true;}')
    # Bind the packaged ARM guest, and the ordinary Linux test services.
    w=core.parent/'native-regs'
    objects=sorted(w.glob('recomp_*.c.o')); assert len(objects)==14
    for obj in objects:
        i=next(i for i,v in enumerate(link) if v.endswith('/'+obj.name.replace('.c.o','.o')))
        link[i]=str(obj)
    link[link.index(str(core/'exact-runtime_test.c.o'))]=str(w/'host-driver.o')
    link[1:1]=[str(w/(n+'.o')) for n in ['entry','gates','checkpoint']]
object_file('vk/backend.cpp',src)
link[link.index('-o')+1]=str(out/'replay')
sp.run(link,cwd=host,check=True)
