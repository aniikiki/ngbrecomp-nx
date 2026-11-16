#pragma once
#include <stdbool.h>
#include <string.h>
#include "recomp_types.h"

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

    typedef float Vector4 __attribute__((vector_size(16)));
    float rows[4][4];
    Vector4 right_rows[4], product[4], term2, term3;
    memcpy(rows, a, sizeof(rows));
    memcpy(right_rows, b, sizeof(right_rows));
    for (unsigned i = 0; i < 4; ++i) {
        Vector4 sum = rows[i][0] * right_rows[0] + rows[i][1] * right_rows[1];
        term2 = rows[i][2] * right_rows[2];
        term3 = rows[i][3] * right_rows[3];
        product[i] = (sum + term2) + term3;
    }
    memcpy(&g_xmm0, &term2, 16);
    memcpy(&g_xmm1, &term3, 16);
    memcpy(&g_xmm2, &product[0], 16);
    memcpy(&g_xmm3, &product[1], 16);
    memcpy(&g_xmm4, &product[2], 16);
    memcpy(&g_xmm5, &product[3], 16);
    return true;
}
