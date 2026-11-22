/* Included by the player build of costume_menu.c. The extra outfits have no
 * retail portraits. Only the costume carousel interprets these private IDs. */
enum { FIRST_EXTRA_PICTURE = 0x7f0c };

struct CostumeGlyph { uint32_t sprite; float width; };
static struct CostumeGlyph costume_glyphs[5];  /* E, X, 1, 2, 3 */
static int costume_font_ready;

/* The base.spr glyph definitions store the atlas width and normalized UVs.
 * Measure them once when the carousel opens, after the menu font loads. */
static int read_costume_font(void)
{
    const uint32_t base_group = 0x452a40, glyph_map = 0x430c48;
    uint32_t defs = MEM32(base_group + 0x1c);
    if (!defs) return 0;
    for (unsigned i = 0; i < 5; i++) {
        uint32_t glyph = MEM32(glyph_map + 4 * "EX123"[i]);
        uint32_t index = glyph - MEM32(base_group + 0x2c);
        if (index >= MEM32(base_group + 0x30)) return 0;
        uint32_t cell = defs + index * 0x18;
        costume_glyphs[i].sprite = glyph;
        costume_glyphs[i].width = (MEMF(cell + 8) - MEMF(cell)) * MEM16(cell + 0x14);
    }
    return 1;
}

static uint32_t ngb_extra_costume_picture(int outfit)
{
    if (outfit == 1) costume_font_ready = read_costume_font();
    return FIRST_EXTRA_PICTURE + outfit - 1;
}

static void queue_costume_sprite(void)
{
    PUSH32(esp, 0x0017773Fu);
    RECOMP_ABI_CALL(0x00221340u, sub_00221340);
}

static void ngb_queue_costume_picture(void)
{
    uint32_t card = edi;
    unsigned extra = MEM32(card) - FIRST_EXTRA_PICTURE;
    if (extra >= EXTRAS) {
        queue_costume_sprite();
        return;
    }

    /* Work on a private sprite request. The title supplies the position,
     * widescreen scale and fade of each card, including its neighbours. */
    esp -= 0x30;
    uint32_t sprite = esp;
    memcpy((void *)XBOX_PTR(sprite), (const void *)XBOX_PTR(card), 0x2c);
    edi = sprite;
    MEM32(sprite) = MEM32(GAME_TABLE);
    MEM32(sprite + 0x28) = 0xff706c85;  /* darken Ryu, keeping the portrait's alpha */
    queue_costume_sprite();
    uint32_t queued = eax;
    if (queued && (costume_font_ready || (costume_font_ready = read_costume_font()))) {
        const struct CostumeGlyph *label[] = {costume_glyphs, costume_glyphs + 1, costume_glyphs + 2 + extra};
        float sx = MEMF(card + 0x14) * 2.0f, sy = MEMF(card + 0x18);
        float x = SMEM16(card + 4) - (label[0]->width + label[1]->width + label[2]->width) * sx * 0.5f;
        MEM16(sprite + 6) = (uint16_t)(SMEM16(card + 6) + lroundf(18.0f * sy));
        MEM16(sprite + 8) = MEM16(card + 8) + 1;
        MEM8(sprite + 0x0a) = 0x10;  /* left edge, vertically centred */
        MEMF(sprite + 0x14) = sx;
        MEMF(sprite + 0x18) = 2.0f * sy;
        MEM32(sprite + 0x28) = 0xfff0f0f0;
        for (unsigned i = 0; i < 3; i++) {
            MEM32(sprite) = label[i]->sprite;
            MEM16(sprite + 4) = (uint16_t)lroundf(x);
            queue_costume_sprite();
            x += label[i]->width * sx;
        }
    }
    edi = card;
    esp += 0x30;
    eax = queued;
}
