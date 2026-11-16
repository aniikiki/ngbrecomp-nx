#include "gloffscreen.h"
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "runtime.h"
#include "scene.h"

struct GloContext { EGLContext ctx; };
static EGLDisplay display;
static EGLContext share;
static EGLConfig config;
void glo_set_current(GloContext *ctx)
{
    if (!eglBindAPI(EGL_OPENGL_API) ||
        !eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,ctx ? ctx->ctx : EGL_NO_CONTEXT))
        ngb_stop("3D make-current failed",eglGetError());
}
GloContext *glo_context_create(void)
{
    if (!display) {
#ifdef __SWITCH__
        display=eglGetDisplay(EGL_DEFAULT_DISPLAY);
#else
        display=eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,NULL);
#endif
        const EGLint attrs[]={EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_SURFACE_TYPE,0,EGL_NONE};
        EGLint count=0;
        if (!eglInitialize(display,NULL,NULL) || !eglBindAPI(EGL_OPENGL_API) ||
            !eglChooseConfig(display,attrs,&config,1,&count) || !count)
            ngb_stop("3D EGL initialization failed",eglGetError());
    }
    GloContext *ctx=calloc(1,sizeof(*ctx));
    if (!ctx) ngb_stop("3D context allocation failed",0);
    const EGLint version[]={EGL_CONTEXT_MAJOR_VERSION,4,EGL_CONTEXT_MINOR_VERSION,3,
        EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT,EGL_NONE};
    ctx->ctx=eglCreateContext(display,config,share,version);
    if (!ctx->ctx) ngb_stop("3D OpenGL 4.3 unavailable",eglGetError());
    glo_set_current(ctx);
    if (!share) {
        share=ctx->ctx;
#ifdef __SWITCH__
        if (!gladLoadGLLoader((GLADloadproc)eglGetProcAddress)) ngb_stop("3D OpenGL entry points",0);
#endif
    }
    return ctx;
}
void glo_context_destroy(GloContext *c)
{
    if (!c) return;
    if (c->ctx==eglGetCurrentContext()) glo_set_current(NULL);
    if (share==c->ctx) share=EGL_NO_CONTEXT;
    eglDestroyContext(display,c->ctx);
    free(c);
}
bool glo_check_extension(const char *name)
{
    GLint count; glGetIntegerv(GL_NUM_EXTENSIONS,&count);
    for(GLint i=0;i<count;i++) if (!strcmp((const char*)glGetStringi(GL_EXTENSIONS,i),name)) return true;
    return false;
}
void glo_readpixels(GLenum format,GLenum type,unsigned bpp,unsigned pitch,unsigned w,unsigned h,bool flip,void *dst)
{
    GLint old_align,old_length;
    glGetIntegerv(GL_PACK_ALIGNMENT,&old_align);
    glGetIntegerv(GL_PACK_ROW_LENGTH,&old_length);
    glPixelStorei(GL_PACK_ALIGNMENT,1);
    glPixelStorei(GL_PACK_ROW_LENGTH,pitch/bpp);
    uint64_t start = ngb_elapsed_ns();
    glReadPixels(0,0,w,h,format,type,dst);
    ngb_scene_count_readback((size_t)w*h*bpp, ngb_elapsed_ns() - start);
    glPixelStorei(GL_PACK_ALIGNMENT,old_align);
    glPixelStorei(GL_PACK_ROW_LENGTH,old_length);
    if(flip) {
        size_t bytes=(size_t)w*bpp;
        unsigned char *tmp=malloc(bytes);
        if(!tmp) ngb_stop("3D readback allocation",bytes);
        for(unsigned i=0;i<h/2;i++) {
            unsigned char *a=(unsigned char *)dst+(size_t)i*pitch;
            unsigned char *b=(unsigned char *)dst+(size_t)(h-i-1)*pitch;
            memcpy(tmp,a,bytes); memcpy(a,b,bytes); memcpy(b,tmp,bytes);
        }
        free(tmp);
    }
}

void glo_shutdown(void)
{
    if (display) {
        eglTerminate(display);
        eglReleaseThread();
        display = EGL_NO_DISPLAY;
    }
}

void glo_shader_error(const char *stage, const char *message)
{
    char line[512];
    snprintf(line, sizeof(line), "3D scene %s: %.440s", stage, message);
    ngb_kernel_log(line);
    ngb_stop("3D renderer failed", 0);
}
