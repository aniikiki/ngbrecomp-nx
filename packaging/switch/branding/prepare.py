"""Generate the private build's hbmenu icon and loading art. Needs Pillow."""
import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[3]
out = root / 'build/switch-runtime/branding'
out.mkdir(exist_ok=True, parents=True)
args = argparse.ArgumentParser()
args.add_argument('--font', type=Path, default=root / 'assets/fonts/LiberationSerif-Bold.ttf')
args = args.parse_args()
original = out / 'original.png'
data = original.read_bytes() if original.exists() else urlopen(
    'https://raw.githubusercontent.com/MobCat/MobCats-original-xbox-game-list/main/icon/5443/5443000D.png',
    timeout=20).read()
if hashlib.sha256(data).hexdigest() != 'cdabace4b7202a9bdcde7ad07b651c08ecf53d81649ede6c24ce1f0f0cb0261d':
    raise ValueError('Unexpected original Xbox icon')
original.write_bytes(data)
art = Image.open(original).convert('RGBA')
bg = '#101014'
# Original Xbox tile stays on the splash; hbmenu uses the official square cover.
cover = out / 'ngb-color.jpg'
color = cover.read_bytes() if cover.exists() else urlopen(
    'https://store-images.s-microsoft.com/image/apps.57582.65292684070648119.ad98b5eb-291c-4d54-bdba-448d32cc1331.48c22332-80c6-452e-8806-610a9c588d93?w=256&h=256&format=jpg',
    timeout=20).read()
if hashlib.sha256(color).hexdigest() != '0dcaae7cf77faba8026f846cee0af5204fd01479502f7a01e95984c063cb1fcb':
    raise ValueError('Unexpected Xbox store cover')
cover.write_bytes(color)
(out / 'ngb-icon.jpg').write_bytes(color)
canvas = Image.new('RGB', (1280, 720), bg)
tile = art.resize((176, 176), Image.Resampling.LANCZOS)
canvas.paste(tile, (552, 165), tile)
draw = ImageDraw.Draw(canvas)
for y, text, size, color in ((406,'NINJA GAIDEN BLACK',44,'#f4f1ed'), (516,'Loading',23,'#c7c3c2')):
    draw.text((640,y), text, anchor='mm', font=ImageFont.truetype(str(args.font),size), fill=color)
draw.rounded_rectangle((608,454,672,457),radius=1,fill='#b33134')
canvas.save(out / 'loading-preview.png')
(out / 'loading.rgba').write_bytes(canvas.resize((640,360),Image.Resampling.LANCZOS).convert('RGBA').tobytes())
