/*
 * Geforce NV2A PGRAPH OpenGL Renderer
 *
 * Copyright (c) 2015 espes
 * Copyright (c) 2015 Jannik Vogel
 * Copyright (c) 2020-2025 Matt Borgerson
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, see <http://www.gnu.org/licenses/>.
 */

#include "qemu/osdep.h"
#include "qemu/fast-hash.h"
#include "qemu/mstring.h"

#include "xemu-version.h"
#include "ui/xemu-settings.h"
#include "hw/xbox/nv2a/pgraph/util.h"
#include "debug.h"
#include "renderer.h"
#ifdef NGB_SWITCH_PGRAPH
#include "runtime.h"
#include "scene.h"
#endif

static GLenum get_gl_primitive_mode(enum ShaderPolygonMode polygon_mode, enum ShaderPrimitiveMode primitive_mode)
{
    switch (primitive_mode) {
    case PRIM_TYPE_POINTS: return GL_POINTS;
    case PRIM_TYPE_LINES: return GL_LINES;
    case PRIM_TYPE_LINE_LOOP: return GL_LINE_LOOP;
    case PRIM_TYPE_LINE_STRIP: return GL_LINE_STRIP;
    case PRIM_TYPE_TRIANGLES: return GL_TRIANGLES;
    case PRIM_TYPE_TRIANGLE_STRIP: return GL_TRIANGLE_STRIP;
    case PRIM_TYPE_TRIANGLE_FAN: return GL_TRIANGLE_FAN;
    case PRIM_TYPE_QUADS: return GL_LINES_ADJACENCY;
    case PRIM_TYPE_QUAD_STRIP: return GL_LINE_STRIP_ADJACENCY;
    case PRIM_TYPE_POLYGON:
        if (polygon_mode == POLY_MODE_LINE) {
            return GL_LINE_LOOP;
        } else if (polygon_mode == POLY_MODE_FILL) {
            return GL_TRIANGLE_FAN;
        }

        assert(!"PRIM_TYPE_POLYGON with invalid polygon_mode");
        return 0;
    default:
        assert(!"Invalid primitive_mode");
        return 0;
    }
}

static GLuint create_gl_shader(GLenum gl_shader_type,
                               const char *code,
                               const char *name)
{
    GLint compiled = 0;

    NV2A_GL_DGROUP_BEGIN("Creating new %s", name);

    NV2A_DPRINTF("compile new %s, code:\n%s\n", name, code);

    GLuint shader = glCreateShader(gl_shader_type);
    glShaderSource(shader, 1, &code, 0);
    glCompileShader(shader);

    /* Check it compiled */
    compiled = 0;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &compiled);
    if (!compiled) {
        GLchar* log;
        GLint log_length;
        glGetShaderiv(shader, GL_INFO_LOG_LENGTH, &log_length);
        log = g_malloc(log_length * sizeof(GLchar));
        glGetShaderInfoLog(shader, log_length, NULL, log);
        fprintf(stderr, "%s\n\n" "nv2a: %s compilation failed: %s\n", code, name, log);
        NV2A_GL_DGROUP_END();
        glo_shader_error(name, log);
    }

    NV2A_GL_DGROUP_END();

    return shader;
}

static void set_texture_sampler_uniforms(ShaderBinding *binding)
{
    for (int i = 0; i < NV2A_MAX_TEXTURES; i++) {
        char samplerName[16];
        snprintf(samplerName, sizeof(samplerName), "texSamp%d", i);
        GLint texSampLoc =
            glGetUniformLocation(binding->gl_program, samplerName);
        if (texSampLoc >= 0) {
            glUniform1i(texSampLoc, i);
        }
    }
}

static unsigned active_count(GLuint program, const char *name, const UniformInfo *info, GLint loc)
{
    if (loc < 0 || info->count == 1 || info->type != UniformElementType_vec4) return info->count;
    GLuint index;
    glGetUniformIndices(program, 1, &name, &index);
    GLint size = 0;
    if (index != GL_INVALID_INDEX) glGetActiveUniformsiv(program, 1, &index, GL_UNIFORM_SIZE, &size);
    return size > 0 ? MIN((unsigned)size, info->count) : info->count;
}

static void update_shader_uniform_locs(ShaderBinding *binding)
{
    char tmp[64];

    for (int i = 0; i < ARRAY_SIZE(binding->uniform_locs.vsh); i++) {
        const char *name = VshUniformInfo[i].name;
        if (VshUniformInfo[i].count > 1) {
            snprintf(tmp, sizeof(tmp), "%s[0]", name);
            name = tmp;
        }
        binding->uniform_locs.vsh[i] = glGetUniformLocation(binding->gl_program, name);
        binding->vsh_counts[i] = active_count(binding->gl_program, name, &VshUniformInfo[i], binding->uniform_locs.vsh[i]);
    }

    for (int i = 0; i < ARRAY_SIZE(binding->uniform_locs.psh); i++) {
        const char *name = PshUniformInfo[i].name;
        if (PshUniformInfo[i].count > 1) {
            snprintf(tmp, sizeof(tmp), "%s[0]", name);
            name = tmp;
        }
        binding->uniform_locs.psh[i] = glGetUniformLocation(binding->gl_program, name);
        binding->psh_counts[i] = active_count(binding->gl_program, name, &PshUniformInfo[i], binding->uniform_locs.psh[i]);
    }
}

typedef struct CompiledShader {
    struct CompiledShader *next;
    MString *source;
    GLenum kind;
    GLuint shader;
    unsigned refs;
} CompiledShader;

typedef struct LinkedShaderProgram {
    struct LinkedShaderProgram *next;
    GLuint shaders[3];
    GLuint program;
    unsigned refs;
    bool uniforms_valid;
    VshUniformValues last_vsh;
    PshUniformValues last_psh;
} LinkedShaderProgram;

static void shader_module_cache_entry_init(Lru *lru, LruNode *node,
                                           const void *key)
{
    ShaderModuleCacheEntry *module =
        container_of(node, ShaderModuleCacheEntry, node);
    memcpy(&module->key, key, sizeof(ShaderModuleCacheKey));

    const char *kind_str;
    MString *code;

    switch (module->key.kind) {
    case GL_VERTEX_SHADER:
        kind_str = "vertex shader";
        code = pgraph_glsl_gen_vsh(&module->key.vsh.state,
                                   module->key.vsh.glsl_opts);
        break;
    case GL_GEOMETRY_SHADER:
        kind_str = "geometry shader";
        code = pgraph_glsl_gen_geom(&module->key.geom.state,
                                    module->key.geom.glsl_opts);
        break;
    case GL_FRAGMENT_SHADER:
        kind_str = "fragment shader";
        code = pgraph_glsl_gen_psh(&module->key.psh.state,
                                   module->key.psh.glsl_opts);
        break;
    default:
        assert(!"Invalid shader module kind");
        kind_str = "unknown";
        code = NULL;
    }

    PGRAPHGLState *r = container_of(lru, PGRAPHGLState, shader_module_cache);
    for (CompiledShader *found = r->compiled_shaders; found; found = found->next) {
        if (found->kind == module->key.kind &&
            !strcmp(mstring_get_str(found->source), mstring_get_str(code))) {
            ++found->refs;
            module->compiled = found;
            mstring_unref(code);
            return;
        }
    }
    CompiledShader *compiled = g_malloc0(sizeof(*compiled));
#ifdef NGB_SWITCH_PGRAPH
    uint64_t start = ngb_elapsed_ns();
#endif
    compiled->shader = create_gl_shader(module->key.kind, mstring_get_str(code), kind_str);
#ifdef NGB_SWITCH_PGRAPH
    ngb_scene_shader_time(0, ngb_elapsed_ns() - start);
#endif
    compiled->source = code;
    compiled->refs = 1;
    compiled->kind = module->key.kind;
    compiled->next = r->compiled_shaders;
    r->compiled_shaders = module->compiled = compiled;
}

static void shader_module_cache_entry_post_evict(Lru *lru, LruNode *node)
{
    ShaderModuleCacheEntry *module =
        container_of(node, ShaderModuleCacheEntry, node);
    CompiledShader *compiled = module->compiled;
    if (--compiled->refs == 0) {
        PGRAPHGLState *r = container_of(lru, PGRAPHGLState, shader_module_cache);
        CompiledShader **slot = &r->compiled_shaders;
        while (*slot != compiled) slot = &(*slot)->next;
        *slot = compiled->next;
        glDeleteShader(compiled->shader);
        mstring_unref(compiled->source);
        g_free(compiled);
    }
}

static bool shader_module_cache_entry_compare(Lru *lru, LruNode *node,
                                              const void *key)
{
    ShaderModuleCacheEntry *module =
        container_of(node, ShaderModuleCacheEntry, node);
    return memcmp(&module->key, key, sizeof(ShaderModuleCacheKey));
}

static GLuint get_shader_module_for_key(PGRAPHGLState *r,
                                        const ShaderModuleCacheKey *key)
{
    uint64_t hash = fast_hash((void *)key, sizeof(ShaderModuleCacheKey));
    LruNode *node = lru_lookup(&r->shader_module_cache, hash, key);
    ShaderModuleCacheEntry *module =
        container_of(node, ShaderModuleCacheEntry, node);
    return module->compiled->shader;
}

static void link_program(GLuint program)
{
    /* link the program */
    glLinkProgram(program);
    GLint linked = 0;
    glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if(!linked) {
        GLchar log[2048];
        glGetProgramInfoLog(program, 2048, NULL, log);
        fprintf(stderr, "nv2a: shader linking failed: %s\n", log);
        glo_shader_error("program link", log);
    }
}

static void generate_shaders(PGRAPHGLState *r, ShaderBinding *binding)
{
    GLuint shaders[3] = {0};

    ShaderState *state = &binding->state;
    ShaderModuleCacheKey key;

    bool need_geometry_shader = pgraph_glsl_need_geom(&state->geom);
    /* Smooth, filled Z-buffered triangles can use the rasterizer's affine
     * interpolation of guest window depth. Other primitives, W buffering
     * and flat provoking vertices retain the NV2A geometry stage. */
    bool interpolate_z = state->geom.smooth_shading && !state->geom.z_perspective &&
        state->geom.polygon_front_mode == POLY_MODE_FILL && state->geom.polygon_back_mode == POLY_MODE_FILL &&
        (state->geom.primitive_mode == PRIM_TYPE_TRIANGLES ||
         state->geom.primitive_mode == PRIM_TYPE_TRIANGLE_STRIP ||
         state->geom.primitive_mode == PRIM_TYPE_TRIANGLE_FAN);
    if (interpolate_z) need_geometry_shader = false;
    if (need_geometry_shader) {
        memset(&key, 0, sizeof(key));
        key.kind = GL_GEOMETRY_SHADER;
        key.geom.state = state->geom;
        shaders[2] = get_shader_module_for_key(r, &key);
    }

    /* create the vertex shader */
    memset(&key, 0, sizeof(key));
    key.kind = GL_VERTEX_SHADER;
    key.vsh.state = state->vsh;
    key.vsh.glsl_opts.interpolate_z = interpolate_z;
    key.vsh.glsl_opts.prefix_outputs = need_geometry_shader;
    shaders[0] = get_shader_module_for_key(r, &key);

    /* generate a fragment shader from register combiners */
    memset(&key, 0, sizeof(key));
    key.kind = GL_FRAGMENT_SHADER;
    key.psh.state = state->psh;
    key.psh.glsl_opts.interpolate_z = interpolate_z;
    shaders[1] = get_shader_module_for_key(r, &key);

    LinkedShaderProgram *linked = r->linked_programs;
    while (linked && memcmp(linked->shaders, shaders, sizeof(shaders)))
        linked = linked->next;
    bool new_program = linked == NULL;
    if (new_program) {
        linked = g_malloc0(sizeof(*linked));
        memcpy(linked->shaders, shaders, sizeof(shaders));
        linked->program = glCreateProgram();
        for (unsigned i = 0; i < 3; ++i)
            if (shaders[i]) glAttachShader(linked->program, shaders[i]);
        linked->next = r->linked_programs;
        r->linked_programs = linked;
    }
    binding->linked = linked;
    ++linked->refs;
    GLuint program = linked->program;
    if (new_program) {
#ifdef NGB_SWITCH_PGRAPH
        uint64_t start = ngb_elapsed_ns();
#endif
        link_program(program);
#ifdef NGB_SWITCH_PGRAPH
        ngb_scene_shader_time(1, ngb_elapsed_ns() - start);
#endif
    }

    glUseProgram(program);

    binding->gl_program = program;
    binding->gl_primitive_mode = get_gl_primitive_mode(
        state->geom.polygon_front_mode, state->geom.primitive_mode);
    binding->initialized = true;

    set_texture_sampler_uniforms(binding);

    /* validate the program */
    GLint valid = 0;
    glValidateProgram(program);
    glGetProgramiv(program, GL_VALIDATE_STATUS, &valid);
    if (!valid) {
        GLchar log[1024];
        glGetProgramInfoLog(program, 1024, NULL, log);
        fprintf(stderr, "nv2a: shader validation failed: %s\n", log);
        glo_shader_error("program validation", log);
    }

    update_shader_uniform_locs(binding);
}

/* libnx keeps the shader LRU in RAM. The process owns no on-disk cache. */
void pgraph_gl_shader_write_cache_reload_list(PGRAPHState *pg)
{
    PGRAPHGLState *r = pg->gl_renderer_state;
    qatomic_set(&r->shader_cache_writeback_pending, false);
    qemu_event_set(&r->shader_cache_writeback_complete);
}

static void shader_cache_entry_init(Lru *lru, LruNode *node, const void *state)
{
    ShaderBinding *binding = container_of(node, ShaderBinding, node);
    memcpy(&binding->state, state, sizeof(ShaderState));
    binding->initialized = false;
    binding->linked = NULL;
}

static void shader_cache_entry_post_evict(Lru *lru, LruNode *node)
{
    ShaderBinding *binding = container_of(node, ShaderBinding, node);
    LinkedShaderProgram *linked = binding->linked;
    if (!linked) return;
    if (--linked->refs == 0) {
        PGRAPHGLState *r = container_of(lru, PGRAPHGLState, shader_cache);
        LinkedShaderProgram **slot = &r->linked_programs;
        while (*slot != linked) slot = &(*slot)->next;
        *slot = linked->next;
        glDeleteProgram(linked->program);
        g_free(linked);
    }
    memset(&binding->state, 0, sizeof(ShaderState));
}

static bool shader_cache_entry_compare(Lru *lru, LruNode *node, const void *key)
{
    ShaderBinding *binding = container_of(node, ShaderBinding, node);
    return memcmp(&binding->state, key, sizeof(ShaderState));
}

void pgraph_gl_init_shaders(PGRAPHState *pg)
{
    PGRAPHGLState *r = pg->gl_renderer_state;

    qemu_mutex_init(&r->shader_cache_lock);
    qemu_event_init(&r->shader_cache_writeback_complete, false);

    /* Linked programs retain driver allocations as well as these entries. */
    const size_t shader_cache_size = 128;
    lru_init(&r->shader_cache);
    r->shader_cache_entries = malloc(shader_cache_size * sizeof(ShaderBinding));
    assert(r->shader_cache_entries != NULL);
    for (int i = 0; i < shader_cache_size; i++) {
        lru_add_free(&r->shader_cache, &r->shader_cache_entries[i].node);
    }

    r->shader_cache.init_node = shader_cache_entry_init;
    r->shader_cache.compare_nodes = shader_cache_entry_compare;
    r->shader_cache.post_node_evict = shader_cache_entry_post_evict;

    const size_t shader_module_cache_size = 256;
    lru_init(&r->shader_module_cache);
    r->shader_module_cache_entries =
        g_malloc_n(shader_module_cache_size, sizeof(ShaderModuleCacheEntry));
    assert(r->shader_module_cache_entries != NULL);
    for (int i = 0; i < shader_module_cache_size; i++) {
        lru_add_free(&r->shader_module_cache, &r->shader_module_cache_entries[i].node);
    }

    r->shader_module_cache.init_node = shader_module_cache_entry_init;
    r->shader_module_cache.compare_nodes = shader_module_cache_entry_compare;
    r->shader_module_cache.post_node_evict = shader_module_cache_entry_post_evict;
}

void pgraph_gl_finalize_shaders(PGRAPHState *pg)
{
    PGRAPHGLState *r = pg->gl_renderer_state;

    // Clear out shader cache
    lru_flush(&r->shader_cache);
    qemu_event_destroy(&r->shader_cache_writeback_complete);
    free(r->shader_cache_entries);
    r->shader_cache_entries = NULL;

    lru_flush(&r->shader_module_cache);
    g_free(r->shader_module_cache_entries);
    r->shader_module_cache_entries = NULL;

    qemu_mutex_destroy(&r->shader_cache_lock);
}

static void apply_uniform_updates(const UniformInfo *info, int *locs,
                                  const unsigned *counts, void *values, void *previous, bool valid, size_t count)
{
    for (int i = 0; i < count; i++) {
        if (locs[i] == -1) {
            continue;
        }

        void *value = (char*)values + info[i].val_offs;

        void *last = (char *)previous + info[i].val_offs;
        unsigned elements = counts[i];
        size_t bytes = info[i].size * elements;
        if (valid && !memcmp(last, value, bytes)) continue;
        if (info[i].type == UniformElementType_vec4 && elements > 1 && valid) {
            /* Matrix palettes often change just a few registers in a large
             * array. Basic array elements occupy consecutive GL locations. */
            float (*src)[4] = value, (*dst)[4] = last;
            unsigned first = 0, end = elements;
            while (!memcmp(dst[first], src[first], sizeof(*src))) ++first;
            while (!memcmp(dst[end - 1], src[end - 1], sizeof(*src))) --end;
            memcpy(dst + first, src + first, (end - first) * sizeof(*src));
            glUniform4fv(locs[i] + first, end - first, src[first]);
            continue;
        }
        memcpy(last, value, bytes);

        switch (info[i].type) {
        case UniformElementType_uint:
            glUniform1uiv(locs[i], info[i].count, value);
            break;
        case UniformElementType_int:
            glUniform1iv(locs[i], info[i].count, value);
            break;
        case UniformElementType_ivec2:
            glUniform2iv(locs[i], info[i].count, value);
            break;
        case UniformElementType_ivec4:
            glUniform4iv(locs[i], info[i].count, value);
            break;
        case UniformElementType_float:
            glUniform1fv(locs[i], info[i].count, value);
            break;
        case UniformElementType_vec2:
            glUniform2fv(locs[i], info[i].count, value);
            break;
        case UniformElementType_vec3:
            glUniform3fv(locs[i], info[i].count, value);
            break;
        case UniformElementType_vec4:
            glUniform4fv(locs[i], elements, value);
            break;
        case UniformElementType_mat2:
            glUniformMatrix2fv(locs[i], info[i].count, GL_FALSE, value);
            break;
        default:
            glo_shader_error("uniform update", "unsupported uniform type");
        }
    }

    assert(glGetError() == GL_NO_ERROR);
}

// FIXME: Consider UBO to align with VK renderer
static void update_shader_uniforms(PGRAPHState *pg, ShaderBinding *binding)
{
    PGRAPHGLState *r = pg->gl_renderer_state;

    LinkedShaderProgram *linked = binding->linked;
    VshUniformValues vsh_values = {0};
    pgraph_glsl_set_vsh_uniform_values(pg, &binding->state.vsh,
                                  binding->uniform_locs.vsh, &vsh_values);
    apply_uniform_updates(VshUniformInfo, binding->uniform_locs.vsh,
                          binding->vsh_counts, &vsh_values, &linked->last_vsh, linked->uniforms_valid, VshUniform__COUNT);

    PshUniformValues psh_values = {0};
    pgraph_glsl_set_psh_uniform_values(pg, binding->uniform_locs.psh, &psh_values);

    for (int i = 0; i < 4; i++) {
        if (r->texture_binding[i] != NULL) {
            float scale = r->texture_binding[i]->scale;
            psh_values.texScale[i] = scale;
        }
    }
    apply_uniform_updates(PshUniformInfo, binding->uniform_locs.psh,
                          binding->psh_counts, &psh_values, &linked->last_psh, linked->uniforms_valid, PshUniform__COUNT);
    linked->uniforms_valid = true;
}

void pgraph_gl_bind_shaders(PGRAPHState *pg)
{
    PGRAPHGLState *r = pg->gl_renderer_state;

    bool binding_changed = false;
    if (r->shader_binding &&
        !pgraph_glsl_check_shader_state_dirty(pg, &r->shader_binding->state)) {
        nv2a_profile_inc_counter(NV2A_PROF_SHADER_BIND_NOTDIRTY);
        goto update_uniforms;
    }

    ShaderBinding *old_binding = r->shader_binding;
    ShaderState state = pgraph_glsl_get_shader_state(pg);

    NV2A_GL_DGROUP_BEGIN("%s (%s)", __func__,
                         state.vsh.is_fixed_function ? "FF" : "PROG");

    qemu_mutex_lock(&r->shader_cache_lock);

    uint64_t shader_state_hash =
        fast_hash((uint8_t *)&state, sizeof(ShaderState));

    LruNode *node = lru_lookup(&r->shader_cache, shader_state_hash, &state);
    ShaderBinding *binding = container_of(node, ShaderBinding, node);

    if (!binding->initialized) {
        nv2a_profile_inc_counter(NV2A_PROF_SHADER_GEN);
        generate_shaders(r, binding);
    }
    assert(binding->initialized);
    r->shader_binding = binding;
    pg->program_data_dirty = false;

    qemu_mutex_unlock(&r->shader_cache_lock);

    binding_changed = (r->shader_binding != old_binding);
    if (binding_changed) {
        nv2a_profile_inc_counter(NV2A_PROF_SHADER_BIND);
        glUseProgram(r->shader_binding->gl_program);
    }

    // FIXME: Clear only the registers that are consumed by this binding.
    pgraph_clear_dirty_reg_map(pg);

    NV2A_GL_DGROUP_END();

update_uniforms:
    assert(r->shader_binding);
    assert(r->shader_binding->initialized);
    update_shader_uniforms(pg, r->shader_binding);
}

GLuint pgraph_gl_compile_shader(const char *vs_src, const char *fs_src)
{
    GLint status;
    char err_buf[512];

    // Compile vertex shader
    GLuint vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &vs_src, NULL);
    glCompileShader(vs);
    glGetShaderiv(vs, GL_COMPILE_STATUS, &status);
    if (status != GL_TRUE) {
        glGetShaderInfoLog(vs, sizeof(err_buf), NULL, err_buf);
        err_buf[sizeof(err_buf)-1] = '\0';
        fprintf(stderr, "Vertex shader compilation failed: %s\n", err_buf);
        glo_shader_error("display shader", err_buf);
    }

    // Compile fragment shader
    GLuint fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &fs_src, NULL);
    glCompileShader(fs);
    glGetShaderiv(fs, GL_COMPILE_STATUS, &status);
    if (status != GL_TRUE) {
        glGetShaderInfoLog(fs, sizeof(err_buf), NULL, err_buf);
        err_buf[sizeof(err_buf)-1] = '\0';
        fprintf(stderr, "Fragment shader compilation failed: %s\n", err_buf);
        glo_shader_error("display shader", err_buf);
    }

    // Link vertex and fragment shaders
    GLuint prog = glCreateProgram();
    glAttachShader(prog, vs);
    glAttachShader(prog, fs);
    glLinkProgram(prog);
    glUseProgram(prog);

    // Flag shaders for deletion (will still be retained for lifetime of prog)
    glDeleteShader(vs);
    glDeleteShader(fs);

    return prog;
}
