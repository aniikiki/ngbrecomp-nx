"""Render the two fixed Loading captions. Run with the Noto Sans CJK SC Regular OTF."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

font = ImageFont.truetype(sys.argv[1], 24)
out = Path(__file__).resolve().parents[1] / 'runtime/loading_labels.h'
captions = ('正在读取图形缓存', '正在准备渲染管线')
with out.open('w') as f:
    f.write("""/* Rendered by branding/loading-labels.py from Noto Sans CJK SC Regular 2.004
 * (SIL Open Font License 1.1). Four pixels per byte, leftmost first. */
#pragma once
enum { loading_label_width = 192, loading_label_height = 30 };
static const unsigned char loading_labels[2][loading_label_height][loading_label_width / 4] = {
""")
    for caption in captions:
        label = Image.new('L', (192, 30))
        ImageDraw.Draw(label).text((96, 15), caption, font=font, anchor='mm', fill=255)
        f.write('    { /* ' + caption + ' */\n')
        for y in range(label.height):
            row = [sum(((label.getpixel((x + i, y)) + 42) // 85) << (6 - 2*i)
                       for i in range(4)) for x in range(0, label.width, 4)]
            f.write('        {' + ','.join(map(str, row)) + '},\n')
        f.write('    },\n')
    f.write('};\n')
