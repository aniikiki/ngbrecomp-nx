// Local offscreen raster regression. Use the generated haze block and the Vulkan backend's slope helper.
#include "gpu/shaders.h"
#include "vk/depth_bias.h"
#include "vk/spirv.h"
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#include <cassert>
#include <cstdio>
#include <vector>
#include <string>
using std::string;
static GLuint shader(GLenum kind,string body){
 auto id=glCreateShader(kind);body="#version 300 es\nprecision highp float;\n"+body;
 const char* ptr=body.c_str();glShaderSource(id,1,&ptr,nullptr);glCompileShader(id);GLint ok;glGetShaderiv(id,GL_COMPILE_STATUS,&ok);
 if(!ok){char log[2048];glGetShaderInfoLog(id,sizeof log,nullptr,log);fprintf(stderr,"%s\n%s\n",log,ptr);abort();}return id;
}
static GLuint program(string frag){
 GLuint p=glCreateProgram();glAttachShader(p,shader(GL_VERTEX_SHADER,R"(
 uniform float dz;
 void main(){vec2 xy=gl_VertexID==0?vec2(-1,-1):gl_VertexID==1?vec2(3,-1):vec2(-1,3);
 gl_Position=vec4(xy,0.20*xy.x+dz,1);})"));
 glAttachShader(p,shader(GL_FRAGMENT_SHADER,"out vec4 col;\n"+frag));glLinkProgram(p);
 GLint ok;glGetProgramiv(p,GL_LINK_STATUS,&ok);assert(ok);return p;
}
static void draw(GLuint p,float dz){glUseProgram(p);glUniform1f(glGetUniformLocation(p,"dz"),dz);glDrawArrays(GL_TRIANGLES,0,3);}
static std::vector<unsigned char> pixels(int w){std::vector<unsigned char> v(w*4);glReadPixels(0,16,w,1,GL_RGBA,GL_UNSIGNED_BYTE,v.data());assert(glGetError()==GL_NO_ERROR);return v;}
int main(){
 auto display=eglGetDisplay(EGL_DEFAULT_DISPLAY);assert(eglInitialize(display,nullptr,nullptr));EGLint attr[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,EGL_DEPTH_SIZE,24,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_NONE};EGLConfig conf;EGLint n;assert(eglChooseConfig(display,attr,&conf,1,&n)&&n);
 EGLint dims[]={EGL_WIDTH,512,EGL_HEIGHT,32,EGL_NONE},ver[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};auto surf=eglCreatePbufferSurface(display,conf,dims);auto ctx=eglCreateContext(display,conf,EGL_NO_CONTEXT,ver);assert(eglMakeCurrent(display,surf,surf,ctx));printf("%s\n",glGetString(GL_RENDERER));
 gpu::PixelKey k{};k.ff[0][0]=2;k.ff[0][1]=2;k.tex[0].kind=gpu::kTex2D;k.proj=1;assert(gpu::PixelHlsl(k).find("float2 hz0;")==string::npos);
 k.alphakill=16;auto source=gpu::PixelHlsl(k);std::vector<uint32_t> spirv;string log;if(!vkr::Compile(source,false,spirv,&log)){fprintf(stderr,"%s\n",log.c_str());return 1;}
 assert(!spirv.empty() && spirv.front()==0x07230203);printf("production haze shader: %zu SPIR-V words\n",spirv.size());
 auto a=source.find("float2 hz0;");assert(a!=string::npos);string block=source.substr(a,source.find("\n}",a)+2-a);
 // GLSL and HLSL share arithmetic here; aliases only adapt types, saturate and raster position.
 for(const auto& [integer,decimal]:{std::pair<string,string>{"> 0 ?","> 0.0 ?"},{"(1 -","(1.0 -"}})
   for(size_t at;(at=block.find(integer))!=string::npos;)block.replace(at,integer.size(),decimal);
 string prefix=R"(
 #define float2 vec2
 #define saturate(x) clamp(x,0.,1.)
 struct Input {vec4 pos;};uniform vec4 surf;uniform sampler2D tex;
 void main(){Input i=Input(gl_FragCoord);vec2 base=i.pos.xy/(surf.xy*surf.w);
 vec4 tc0=vec4(base+vec2(0.018,0),0,1),texsize[1];texsize[0]=vec4(0);
 )";
 auto old=program(prefix+"col=texture(tex,tc0.xy);}");
 auto fixed=program(prefix+block+"\ncol=texture(tex,hz0);}");
 GLuint t;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);unsigned char tex[256*4]={};for(int i=0;i<256;i++)tex[i*4]=(i==255?255:i%128);
 glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,256,1,0,GL_RGBA,GL_UNSIGNED_BYTE,tex);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
 auto wall=program("void main(){col=vec4(0,0,0,1);}");auto light=program("void main(){col=vec4(1,0,0,1);}");
 for(int scale:{1,2}){
 int w=256*scale;glViewport(0,0,w,32);glDisable(GL_DEPTH_TEST);
 auto haze=[&](GLuint p){glUseProgram(p);glUniform4f(glGetUniformLocation(p,"surf"),256,32.f/scale,0,scale);draw(p,0);return pixels(w);};
 auto before=haze(old),after=haze(fixed);int ob=0,nb=0;
 for(int x=0;x<w;x++){if(x<w*.96)assert(before[x*4]==after[x*4]);ob+=before[x*4]==255;nb+=after[x*4]==255;}
 assert(nb<ob && nb>0);
 glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LEQUAL);
 auto depth=[&](float slope){glDepthMask(GL_TRUE);glClear(GL_DEPTH_BUFFER_BIT|GL_COLOR_BUFFER_BIT);draw(wall,0);
 glEnable(GL_SCISSOR_TEST);glScissor(0,0,w/4,32);draw(wall,-.1f);glDisable(GL_SCISSOR_TEST);
 glDepthMask(GL_FALSE);glEnable(GL_POLYGON_OFFSET_FILL);glPolygonOffset(slope,0);draw(light,.4f*1.75f/256);glDisable(GL_POLYGON_OFFSET_FILL);
 auto v=pixels(w);int hits=0;for(int x=0;x<w;x++){if(x<w/4)assert(v[x*4]==0);hits+=v[x*4]!=0;}return hits;};
 assert(gpu::ScaledSlopeBias(-1,scale,true,3)==-scale);
 int oldhits=depth(-1),hits=depth(gpu::ScaledSlopeBias(-1,scale,false,3));assert(oldhits<hits && hits==w*3/4);
 printf("%dx: clamped-edge pixels %d -> %d; visible overlay pixels %d -> %d/%d; occluder intact\n",scale,ob,nb,oldhits,hits,w*3/4);
 }
}
