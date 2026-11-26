#pragma once
#include <stdbool.h>
#include <string.h>
#include "recomp_types.h"

typedef float NgbMatrixRow __attribute__((vector_size(16)));
static inline NgbMatrixRow ngb_product_row(const float a[4], const NgbMatrixRow b[4],
                                           NgbMatrixRow *term2, NgbMatrixRow *term3)
{
    NgbMatrixRow sum = a[0] * b[0] + a[1] * b[1];
    *term2 = a[2] * b[2];
    *term3 = a[3] * b[3];
    return (sum + *term2) + *term3;
}

/* Both XDK matrix routines have the same SSE arithmetic. The original
 * stores take place after all inputs have been read, allowing in-place
 * multiplication. Keep the intermediate XMM registers visible to callers. */
static inline bool ngb_matrix_product(uint32_t left, uint32_t right)
{
    if ((left & 4095) > 4096 - 64 || (right & 4095) > 4096 - 64)
        return false;
    const void *a = ngb_guest_vector_page(left);
    const void *b = ngb_guest_vector_page(right);
    if (!a || !b) return false;

    float rows[4][4];
    NgbMatrixRow right_rows[4], product[4], term2, term3;
    memcpy(rows, a, sizeof(rows));
    memcpy(right_rows, b, sizeof(right_rows));
    for (unsigned i = 0; i < 4; ++i) {
        product[i] = ngb_product_row(rows[i], right_rows, &term2, &term3);
    }
    memcpy(&g_xmm0, &term2, 16);
    memcpy(&g_xmm1, &term3, 16);
    memcpy(&g_xmm2, &product[0], 16);
    memcpy(&g_xmm3, &product[1], 16);
    memcpy(&g_xmm4, &product[2], 16);
    memcpy(&g_xmm5, &product[3], 16);
    return true;
}
