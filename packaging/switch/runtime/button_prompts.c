#include "runtime.h"

/* Keep the UVs as their original float bit patterns. */
struct SpriteCell {
    uint32_t u0, v0, u1, v1;
    uint32_t texture, dimensions;
};

/* Inline button glyphs and move lists use 5/6. A held button uses 0x1ce/1cf
 * with the arrow already in the atlas. Select the other cell on registration. */
void ngb_switch_xy_prompts(const uint32_t *group)
{
    uint32_t first = group[0x2c / 4];
    unsigned index;
    switch (first) {
    case 0:     index = 5; break;
    case 0x161: index = 0x1ce - 0x161; break;
    default:    return;
    }
    uint32_t defs = group[0x1c / 4];
    if (defs < 4 || group[0x30 / 4] < index + 2) return;
    const uint32_t *size = (const uint32_t *)ngb_guest_pointer(defs - 4, 4);
    if (*size < (index + 2) * sizeof(struct SpriteCell)) return;

    struct SpriteCell *x = (struct SpriteCell *)ngb_guest_pointer(
        defs + index * sizeof(*x), 2 * sizeof(*x));
    struct SpriteCell *y = x + 1;
    /* The two equal cells share an atlas row. The order check also handles
     * unloading and registering the same in-memory resource a second time. */
    if (x->u0 != 0 || x->u1 != y->u0 || !y->u0 ||
        x->v0 != y->v0 || x->v1 != y->v1 ||
        x->texture != y->texture || x->dimensions != y->dimensions) return;
    uint32_t middle = y->u0;
    x->u0 = middle;
    x->u1 = y->u1;
    y->u0 = 0;
    y->u1 = middle;
}
