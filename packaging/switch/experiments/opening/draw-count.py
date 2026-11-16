"""Count title API entries and draws produced by each path on the same scene flips."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
vk='--vk' in sys.argv
p=NativeProbe('opening-draw-count-vk' if vk else 'opening-draw-count')
s=(ROOT/'src/d3d/hle.cpp').read_text()
k='void Draw(uint32_t prim, uint32_t start, uint32_t count, const uint8_t* indices) {'
assert s.count(k)==1
s=s.replace(k,'''static unsigned dc_api[4], dc_draws[2], dc_active;
extern "C" void dc_flip(unsigned f){
 if(f==0){dc_active=1;return;}
 if(f==30||f==120)fprintf(stderr,"[DRAW_COUNT] %u index=%u plain=%u up=%u push=%u emitted_index=%u emitted_plain=%u\\n",f,dc_api[0],dc_api[1],dc_api[2],dc_api[3],dc_draws[1],dc_draws[0]);
}
'''+k+'\n if(dc_active && g_backend)++dc_draws[indices!=nullptr];')
for i,name in enumerate(('DrawIndexedVertices','DrawVertices','DrawVerticesUP','RunPushBuffer')):
 k='case D3DF_D3DDevice_'+name+':';assert s.count(k)==1;s=s.replace(k,k+f' if(dc_active)++dc_api[{i}];')
p.add('hle.cpp',s)
if vk:
 v=(ROOT/'src/d3d/vk/backend.cpp').read_text()
 k='void VulkanBackend::Draw(';assert v.count(k)==1
 v=v.replace(k,'static unsigned vk_i,vk_p;\n'+k)
 for counter,call in [('vk_i','d_.vkCmdDrawIndexed(cmd_, a.index_count, 1, 0, a.base_vertex, 0);'),('vk_p','d_.vkCmdDraw(cmd_, a.draw_count, 1, 0, 0);')]:
  assert v.count(call)==1;v=v.replace(call,'{++'+counter+';'+call+'}')
 k='    frame_++;';assert v.count(k)==1;v=v.replace(k,k+' if(frame_==30||frame_==120)fprintf(stderr,"[VK_COUNT] %u %u %u\\n",frame_,vk_i,vk_p);')
 p.link[p.link.index(str(REGS/'backend-host-clip.o'))]=p.compile('vk/backend.cpp',v,['-DNGB_RIGID_CLIP'])
 ds=(REGS/'host-driver.c').read_text().replace('ngb_stop("verified 120 original demo frames", 120);','fprintf(stderr,"[DRAW_MOTION_OK] 120\\n");')
 p.link[p.link.index(str(p.core/'exact-runtime_test.c.o'))]=p.compile('runtime_test.c',ds,['-I'+str(REGS),'-I'+str(RUNTIME),'-include',str(RUNTIME/'switch_guest_regs.h'),'-DNGB_RIGID_CLIP','-DNGB_REGISTER_PACKAGE'])
else:p.driver('')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void dc_flip(unsigned);dc_flip({f});')
if vk:s=s.replace('dc_flip(scene_flips);','dc_flip(scene_flips);if(scene_flips==124)ngb_stop("completed draw count",124);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
