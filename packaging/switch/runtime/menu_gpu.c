#include "menu_gpu.h"
#include "runtime.h"
#include "scanout.h"
#include "d3d/d3d8_swizzle.h"
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <stdlib.h>
#include <string.h>

enum { MAX_DIM = 512, SLOTS = 8 };
struct alpha_texture {
    const uint8_t *address;
    unsigned w, h;
    GLuint name;
    uint8_t snapshot[MAX_DIM*MAX_DIM];
};

static struct {
    EGLDisplay display;
    EGLContext context;
    int enabled, attempted, ready;
    GLuint fbo, target, vertices;
    unsigned stride, replace, draws, batches;
    uint64_t read_ns;
    struct alpha_texture textures[SLOTS];
} gpu;
uintptr_t ngb_menu_dirty_begin, ngb_menu_dirty_end;

/* Row zero of guest memory is also row zero of the offscreen GL image.
 * Match the NV2A integer pixel centres and keep the guest's BGRA byte order. */
static const char vertex_source[] =
    "#version 300 es\n"
    "layout(location=0) in vec2 xy; layout(location=1) in vec2 uv;"
    "layout(location=2) in vec4 color; uniform vec2 extent;"
    "out highp vec2 tc; out highp vec4 tint;"
    "void main(){ gl_Position=vec4((xy+0.5)*2.0/extent-1.0,0,1); tc=uv; tint=color; }";
static const char fragment_source[] =
    "#version 300 es\nprecision highp float; uniform highp sampler2D maskTex;"
    "in vec2 tc; in vec4 tint; out vec4 pixel;"
    "void main(){pixel=vec4(tint.rgb,texture(maskTex,tc).r*tint.a);}";

static GLuint compile(GLenum type, const char *source)
{
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, NULL);
    glCompileShader(shader);
    GLint ok = 0;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &ok);
    if (ok) return shader;
    glDeleteShader(shader);
    return 0;
}

static int initialize(void)
{
#ifndef __SWITCH__
    if (getenv("NGB_TEST_CPU_MENU")) return 0;
    gpu.display = eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
#else
    gpu.display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
#endif
    if (!gpu.display || !eglInitialize(gpu.display, NULL, NULL) || !eglBindAPI(EGL_OPENGL_ES_API))
        return 0;
    EGLConfig config;
    EGLint count = 0;
    const EGLint attrs[] = {EGL_SURFACE_TYPE, 0, EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT_KHR, EGL_NONE};
    const EGLint version[] = {EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE};
    if (!eglChooseConfig(gpu.display, attrs, &config, 1, &count) || !count) return 0;
    gpu.context = eglCreateContext(gpu.display, config, EGL_NO_CONTEXT, version);
    if (!gpu.context || !eglMakeCurrent(gpu.display, EGL_NO_SURFACE, EGL_NO_SURFACE, gpu.context)) return 0;
    GLuint vs = compile(GL_VERTEX_SHADER, vertex_source), fs = compile(GL_FRAGMENT_SHADER, fragment_source);
    if (!vs || !fs) return 0;
    GLuint program = glCreateProgram();
    glAttachShader(program, vs);
    glAttachShader(program, fs);
    glLinkProgram(program);
    glDeleteShader(vs);
    glDeleteShader(fs);
    GLint linked = 0;
    glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (!linked) return 0;
    glUseProgram(program);
    glUniform2f(glGetUniformLocation(program, "extent"), NGB_SCAN_W, NGB_SCAN_H);

    glGenTextures(1, &gpu.target);
    glBindTexture(GL_TEXTURE_2D, gpu.target);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, NGB_SCAN_W, NGB_SCAN_H);
    glGenFramebuffers(1, &gpu.fbo);
    glBindFramebuffer(GL_FRAMEBUFFER, gpu.fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, gpu.target, 0);
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) return 0;
    glViewport(0, 0, NGB_SCAN_W, NGB_SCAN_H);
    glDisable(GL_DITHER);
    glEnable(GL_BLEND);
    glGenBuffers(1, &gpu.vertices);
    glBindBuffer(GL_ARRAY_BUFFER, gpu.vertices);
    for (unsigned i=0; i<3; ++i) glEnableVertexAttribArray(i);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, sizeof(struct screen_vertex), NULL);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, sizeof(struct screen_vertex),
                          (void *)offsetof(struct screen_vertex,u));
    glVertexAttribPointer(2, 4, GL_UNSIGNED_BYTE, GL_TRUE, sizeof(struct screen_vertex),
                          (void *)offsetof(struct screen_vertex,color));
    /* Some drivers compile the hardware program on the first draw. Warm
     * both blend states in the private target before the interactive fade. */
    GLuint mask;
    const uint8_t white=255;
    const struct screen_vertex quad[] = {
        {0,0,0,1,UINT32_MAX,0,0}, {1,0,0,1,UINT32_MAX,1,0},
        {0,1,0,1,UINT32_MAX,0,1}, {1,1,0,1,UINT32_MAX,1,1}
    };
    glGenTextures(1,&mask);
    glBindTexture(GL_TEXTURE_2D,mask);
    glTexStorage2D(GL_TEXTURE_2D,1,GL_R8,1,1);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RED,GL_UNSIGNED_BYTE,&white);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);
    glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad,GL_STREAM_DRAW);
    glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
    glDrawArrays(GL_TRIANGLE_STRIP,0,4);
    glBlendFunc(GL_SRC_ALPHA,GL_ONE);
    glDrawArrays(GL_TRIANGLE_STRIP,0,4);
    glFinish();
    glDeleteTextures(1,&mask);
    if (glGetError() != GL_NO_ERROR) return 0;
    char message[150];
    snprintf(message,sizeof(message),"Main menu overlay renderer=%s",glGetString(GL_RENDERER));
    ngb_kernel_log(message);
    return 1;
}

static GLuint alpha_mask(const uint8_t *src, unsigned w, unsigned h)
{
    static uint8_t linear[MAX_DIM*MAX_DIM];
    struct alpha_texture *slot = NULL;
    for (unsigned i=0; i<SLOTS; ++i) {
        struct alpha_texture *t = &gpu.textures[i];
        if (t->address == src && t->w == w && t->h == h) {
            if (!memcmp(src,t->snapshot,w*h)) return t->name;
            slot = t;
            break;
        }
    }
    if (!slot) slot = &gpu.textures[gpu.replace++ % SLOTS];
    unsigned mx, my;
    xbox_swizzle_masks(w,h,&mx,&my);
    for (unsigned y=0, row=0; y<h; ++y, row=(row-my)&my)
        for (unsigned x=0, col=0; x<w; ++x, col=(col-mx)&mx)
            linear[y*w+x] = src[row|col];
    if (!slot->name) glGenTextures(1,&slot->name);
    glBindTexture(GL_TEXTURE_2D,slot->name);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
    glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    glTexImage2D(GL_TEXTURE_2D,0,GL_R8,w,h,0,GL_RED,GL_UNSIGNED_BYTE,linear);
    if (glGetError() != GL_NO_ERROR) return 0;
    slot->address = src; slot->w = w; slot->h = h;
    memcpy(slot->snapshot,src,w*h);
    return slot->name;
}

void ngb_menu_gpu_flush(void)
{
    if (!ngb_menu_dirty_end) return;
    uint64_t start = ngb_elapsed_ns();
    glPixelStorei(GL_PACK_ROW_LENGTH,gpu.stride);
    glReadPixels(0,0,NGB_SCAN_W,NGB_SCAN_H,GL_RGBA,GL_UNSIGNED_BYTE,(void *)ngb_menu_dirty_begin);
    ngb_menu_dirty_begin = ngb_menu_dirty_end = 0;
    GLenum error = glGetError();
    if (error) ngb_stop("menu overlay readback failed",error);
    gpu.read_ns += ngb_elapsed_ns()-start;
    ++gpu.batches;
}

void ngb_menu_gpu_prepare(void)
{
    if (!gpu.attempted) {
        gpu.attempted = 1;
        gpu.ready = initialize();
        if (!gpu.ready) {
            char msg[96];
            snprintf(msg,sizeof(msg),"Main menu overlay renderer=CPU (EGL %04x)",eglGetError());
            ngb_kernel_log(msg);
        }
    }
}

void ngb_menu_gpu_enable(void) { gpu.enabled = 1; }

int ngb_menu_gpu_overlay(const struct screen_vertex v[4], const uint8_t *texture,
                         unsigned tw, unsigned th, uint32_t *dst, unsigned stride,
                         unsigned width, unsigned height, int additive)
{
    if (!gpu.enabled || width != NGB_SCAN_W || height != NGB_SCAN_H ||
        tw > MAX_DIM || th > MAX_DIM || (tw < 256 && th < 256 && !ngb_menu_dirty_end)) return 0;
    for (unsigned i=1; i<4; ++i) if (v[i].color != v[0].color) return 0;
    ngb_menu_gpu_prepare();
    if (!gpu.ready) return 0;
    uintptr_t address=(uintptr_t)dst, end=address+((size_t)(height-1)*stride+width)*4;
    if ((uintptr_t)texture < end && (uintptr_t)texture+tw*th > address) return 0;
    if (ngb_menu_dirty_begin != address || stride != gpu.stride) ngb_menu_gpu_flush();
    GLuint mask=alpha_mask(texture,tw,th);
    if (!mask) ngb_stop("menu alpha texture upload failed",tw);
    if (!ngb_menu_dirty_end) {
        glBindTexture(GL_TEXTURE_2D,gpu.target);
        glPixelStorei(GL_UNPACK_ROW_LENGTH,stride);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,width,height,GL_RGBA,GL_UNSIGNED_BYTE,dst);
        glPixelStorei(GL_UNPACK_ROW_LENGTH,0);
        gpu.stride = stride;
        ngb_menu_dirty_begin = address; ngb_menu_dirty_end = end;
    }
    glBindTexture(GL_TEXTURE_2D,mask);
    glBufferData(GL_ARRAY_BUFFER,sizeof(*v)*4,v,GL_STREAM_DRAW);
    glBlendFunc(GL_SRC_ALPHA,additive ? GL_ONE : GL_ONE_MINUS_SRC_ALPHA);
    glDrawArrays(GL_TRIANGLE_STRIP,0,4);
    ++gpu.draws;
    return 1;
}

void ngb_menu_gpu_report(void)
{
    if (!gpu.ready) return;
    char msg[112];
    snprintf(msg,sizeof(msg),"Main menu GPU draws=%u readbacks=%u readback_ms=%llu",
             gpu.draws,gpu.batches,(unsigned long long)(gpu.read_ns/1000000));
    ngb_kernel_log(msg);
    gpu.draws=gpu.batches=0;
    gpu.read_ns=0;
}

void ngb_menu_gpu_close(void)
{
    ngb_menu_dirty_begin = ngb_menu_dirty_end = 0;
    if (gpu.context) {
        eglMakeCurrent(gpu.display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
        eglDestroyContext(gpu.display,gpu.context);
    }
    if (gpu.display) eglTerminate(gpu.display);
    if (gpu.attempted) eglReleaseThread();
    memset(&gpu,0,sizeof(gpu));
}
