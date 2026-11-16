#pragma once

#include "recomp_types.h"
#include <arm_neon.h>
#include <stdbool.h>
#include <string.h>

static inline bool ngb_arm_finite(float32x4_t v)
{
    uint32x4_t magnitude = vandq_u32(vreinterpretq_u32_f32(v), vdupq_n_u32(0x7fffffff));
    return vmaxvq_u32(magnitude) < 0x7f800000;
}

/* In this range, products have exponents within [-60, 61]. Cancellation
 * between two rounded products still fits in the binary32 normal range.
 * Outside it, the generated x87 path also models extended-exponent results. */
static inline uint32x4_t ngb_arm_dot_range(float32x4_t value)
{
    uint32x4_t mag = vandq_u32(vreinterpretq_u32_f32(value), vdupq_n_u32(0x7fffffff));
    return vorrq_u32(vceqq_u32(mag, vdupq_n_u32(0)),
                     vandq_u32(vcgeq_u32(mag, vdupq_n_u32(97u << 23)),
                               vcleq_u32(mag, vdupq_n_u32(157u << 23))));
}

static inline bool ngb_arm_x87_row(uint32_t matrix, uint32_t dest, bool column)
{
    /* The original four dot products have three intervening polls. Leave any
     * due event at its exact guest instruction, including partial stores. */
    if (ngb_pending_dpcs || ngb_poll_mask < 3 ||
        (ngb_guest_polls & ngb_poll_mask) > ngb_poll_mask - 3) return false;
    const void *src = ngb_ram_span(matrix, 64);
    unsigned char *out = ngb_ram_span(dest, column ? 52 : 16);
    if (!src || !out) return false;
    uintptr_t a = (uintptr_t)src, b = (uintptr_t)out;
    if (a < b + (column ? 52 : 16) && b < a + 64) return false;
    unsigned t = g_fp_top;
    float k[4];
    for (unsigned i = 0; i < 4; ++i)
        k[i] = (float)g_fp_stack[(t + 3 - i) & 7];
    float32x4x4_t row = column ? vld4q_f32(src) : vld1q_f32_x4(src);
    uint32x4_t valid = ngb_arm_dot_range(vld1q_f32(k));
    for (unsigned i = 0; i < 4; ++i)
        valid = vandq_u32(valid, ngb_arm_dot_range(row.val[i]));
    if (!vminvq_u32(valid)) return false;

    /* The last lane determines the four popped physical x87 stack slots. */
    float32x4_t result;
    if (!(g_fp_control_word & 0x300u)) {
        float32x4_t p0 = vmulq_n_f32(row.val[0], k[0]);
        float32x4_t p1 = vmulq_n_f32(row.val[1], k[1]);
        float32x4_t p2 = vmulq_n_f32(row.val[2], k[2]);
        float32x4_t p3 = vmulq_n_f32(row.val[3], k[3]);
        float32x4_t odd = vaddq_f32(p1, p3);
        result = vaddq_f32(vaddq_f32(p2, p0), odd);
        g_fp_stack[(t + 4) & 7] = vgetq_lane_f32(p0, 3);
        g_fp_stack[(t + 5) & 7] = vgetq_lane_f32(p3, 3);
        g_fp_stack[(t + 6) & 7] = vgetq_lane_f32(odd, 3);
        g_fp_stack[(t + 7) & 7] = vgetq_lane_f32(result, 3);
    } else {
        float32x2_t half[2];
        for (unsigned j = 0; j < 2; ++j) {
            float64x2_t products[4];
            for (unsigned i = 0; i < 4; ++i) {
                float32x2_t pair = j ? vget_high_f32(row.val[i]) : vget_low_f32(row.val[i]);
                products[i] = vmulq_n_f64(vcvt_f64_f32(pair), k[i]);
            }
            float64x2_t odd = vaddq_f64(products[1], products[3]);
            float64x2_t sum = vaddq_f64(vaddq_f64(products[2], products[0]), odd);
            half[j] = vcvt_f32_f64(sum);
            if (j) {
                g_fp_stack[(t + 4) & 7] = vgetq_lane_f64(products[0], 1);
                g_fp_stack[(t + 5) & 7] = vgetq_lane_f64(products[3], 1);
                g_fp_stack[(t + 6) & 7] = vgetq_lane_f64(odd, 1);
                g_fp_stack[(t + 7) & 7] = vgetq_lane_f64(sum, 1);
            }
        }
        result = vcombine_f32(half[0], half[1]);
    }
    if (column) {
        float values[4];
        vst1q_f32(values, result);
        for (unsigned i = 0; i < 4; ++i) memcpy(out + i * 16, values + i, 4);
    } else {
        memcpy(out, &result, 16);
    }
    ngb_guest_polls += 3;
    return true;
}

/* Transform three point/direction components against the guest matrix.
 * Publish the same three XMM registers before the original output store. */
static inline bool ngb_arm_transform(uint32_t source, uint32_t matrix, bool translate)
{
    const void *v = ngb_ram_span(source, 12);
    const unsigned char *m = ngb_ram_span(matrix, translate ? 64 : 48);
    if (!v || !m) return false;
    float xyz[3];
    float32x4_t rows[4];
    memcpy(xyz, v, sizeof(xyz));
    memcpy(rows, m, translate ? 64 : 48);
    if (!isfinite(xyz[0]) || !isfinite(xyz[1]) || !isfinite(xyz[2]) ||
        !ngb_arm_finite(rows[0]) || !ngb_arm_finite(rows[1]) ||
        !ngb_arm_finite(rows[2]) || (translate && !ngb_arm_finite(rows[3]))) return false;
    float32x4_t x = vmulq_f32(vdupq_n_f32(xyz[0]), rows[0]);
    float32x4_t y = vmulq_f32(vdupq_n_f32(xyz[1]), rows[1]);
    float32x4_t z = vmulq_f32(vdupq_n_f32(xyz[2]), rows[2]);
    if (translate) x = vaddq_f32(x, rows[3]);
    float32x4_t sum = vaddq_f32(vaddq_f32(x, y), z);
    memcpy(&g_xmm1, &y, sizeof(y));
    memcpy(&g_xmm2, &sum, sizeof(sum));
    memcpy(&g_xmm3, &z, sizeof(z));
    return true;
}
