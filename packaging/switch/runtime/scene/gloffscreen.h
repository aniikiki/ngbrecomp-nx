#pragma once
#include <stdbool.h>
#ifdef __SWITCH__
#include <glad/glad.h>
#else
#define GL_GLEXT_PROTOTYPES 1
#include <GL/gl.h>
#include <GL/glext.h>
#endif
typedef struct GloContext GloContext;
GloContext *glo_context_create(void);
void glo_context_destroy(GloContext*);
void glo_set_current(GloContext*);
bool glo_check_extension(const char*);
void glo_readpixels(GLenum format, GLenum type, unsigned bpp, unsigned pitch,unsigned width,unsigned height,bool flip,void *dst);
#ifdef __SWITCH__
#include <GL/glext.h>
#endif
void glo_shutdown(void);
void glo_shader_error(const char *stage, const char *message) __attribute__((noreturn));
