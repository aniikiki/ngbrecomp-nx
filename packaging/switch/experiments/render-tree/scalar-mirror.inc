// Fast ABI for the running native renderer. A detail frame must still include
// the complete instrumentation span; never short-circuit it halfway through.
extern "C" unsigned char *ngb_fast_ram;
extern "C" unsigned short ngb_fast_page_bytes[];
extern "C" int scalar_mirror(int fn,uint32_t ax,uint32_t cx,uint32_t dx,uint32_t sp,uint32_t bx){
 if(!g_backend||g_mirror||ngb_direct_detail_frame)return 0;
 uint32_t arg=0;
 switch(fn){
 case D3DF_D3DDevice_SetRenderState_Simple:
    if(!g_take[fn])return 0;
    g_state.simple[(cx&0x1ffc)>>2]=dx;return 2;
 case D3DF_D3DDevice_SetVertexShaderConstant1:
 case D3DF_D3DDevice_SetVertexShaderConstant4:
    // Before's default does nothing; constants are read at each draw.
    return 1;
 default:break;
 }
 uint32_t a=sp+4;
 if((a&4095)+4>ngb_fast_page_bytes[a>>12])return 0;
 std::memcpy(&arg,ngb_fast_ram+(a&0x7fffffffu),4);
 switch(fn){
 case D3DF_D3DDevice_SetTexture:g_state.textures[ax&3]=arg;break;
 case D3DF_D3DDevice_SetStreamSource:g_state.streams[ax&15]={bx,arg};break;
 case D3DF_D3DDevice_LightEnable:if(ax<8)g_state.light_enable=arg?g_state.light_enable|(1u<<ax):g_state.light_enable&~(1u<<ax);break;
 case D3DF_D3DDevice_SetRenderState_TextureFactor:g_state.rs[gpu::kRsTextureFactor]=arg;break;
 case D3DF_D3DDevice_SetRenderState_VertexBlend:g_state.rs[gpu::kRsVertexBlend]=arg;break;
 default:return 0;
 }
 return 1;
}
