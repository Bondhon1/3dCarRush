"""Generate the game's brand assets (run once; outputs committed to assets/).

  python tools/make_logo.py

Produces:
  assets/logo.png  -- wide transparent wordmark shown on the start menu
  assets/icon.ico  -- multi-size app icon used by the PyInstaller build
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

# palette (matches the in-game dusk theme)
CYAN = (60, 220, 240)
BLUE = (40, 120, 220)
DEEP = (10, 16, 30)
RED = (220, 55, 60)
WHITE = (245, 250, 255)


def _font(size, bold=True):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "impact.ttf",
                 "segoeuib.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _vgradient(size, top, bottom):
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return grad.resize((w, h))


def _shear(img, factor=-0.22):
    """Italic slant (negative leans the tops to the right)."""
    w, h = img.size
    xshift = abs(factor) * h
    new_w = w + int(xshift)
    return img.transform((new_w, h), Image.AFFINE,
                         (1, factor, xshift if factor < 0 else 0, 0, 1, 0),
                         resample=Image.BICUBIC)


def _checker(draw, x, y, cols, rows, cell, c1=WHITE, c2=DEEP):
    for r in range(rows):
        for c in range(cols):
            col = c1 if (r + c) % 2 == 0 else c2
            draw.rectangle([x + c * cell, y + r * cell,
                            x + (c + 1) * cell, y + (r + 1) * cell], fill=col)


# ---------------------------------------------------------------------------
# Wide wordmark
# ---------------------------------------------------------------------------
def make_logo():
    W, H = 1040, 300
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    text = "3D CAR RUSH"
    # auto-fit the font so the wordmark fills a target width (leaving room for
    # the slant, glow and the chevrons on the left)
    target_w = 720
    size = 150
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    for _ in range(6):
        font = _font(size)
        box = tmp.textbbox((0, 0), text, font=font)
        tw = box[2] - box[0]
        if abs(tw - target_w) < 8 or tw == 0:
            break
        size = max(20, int(size * target_w / tw))
    font = _font(size)
    box = tmp.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]

    # text alpha mask on its own layer, then slanted for a speedy italic
    mask = Image.new("L", (tw + 40, th + 40), 0)
    ImageDraw.Draw(mask).text((20 - box[0], 20 - box[1]), text, font=font, fill=255)
    mask = _shear(mask, -0.20)
    mw, mh = mask.size

    # cyan->blue gradient poured through the mask
    grad = _vgradient((mw, mh), CYAN, BLUE).convert("RGBA")
    grad.putalpha(mask)

    ox, oy = (W - mw) // 2, (H - mh) // 2 - 6

    # soft outer glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gl = Image.new("RGBA", (mw, mh), (0, 0, 0, 0))
    gl.putalpha(mask)
    tinted = Image.new("RGBA", (mw, mh), CYAN + (255,))
    tinted.putalpha(mask)
    glow.paste(tinted, (ox, oy), tinted)
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    img = Image.alpha_composite(img, glow)

    # drop shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", (mw, mh), (0, 0, 0, 0))
    sh.putalpha(mask)
    black = Image.new("RGBA", (mw, mh), (0, 0, 0, 200))
    black.putalpha(mask)
    shadow.paste(black, (ox + 6, oy + 8), black)
    shadow = shadow.filter(ImageFilter.GaussianBlur(3))
    img = Image.alpha_composite(img, shadow)

    # the gradient text itself
    img.alpha_composite(grad, (ox, oy))

    d = ImageDraw.Draw(img)
    # checkered flag ribbon under the wordmark
    ribbon_y = oy + mh - 18
    _checker(d, ox + 8, ribbon_y, cols=(mw - 40) // 18, rows=2, cell=18)
    # red speed underline
    d.rectangle([ox + 6, ribbon_y + 40, ox + mw - 30, ribbon_y + 48], fill=RED + (255,))

    # speed chevrons on the left
    cx = ox - 26
    for i in range(3):
        xx = cx - i * 22
        d.polygon([(xx, oy + mh // 2 - 40), (xx + 26, oy + mh // 2),
                   (xx, oy + mh // 2 + 40), (xx + 12, oy + mh // 2),
                   ], fill=(CYAN[0], CYAN[1], CYAN[2], 210 - i * 55))

    img.save(os.path.join(ASSETS, "logo.png"))
    print("wrote assets/logo.png", img.size)


# ---------------------------------------------------------------------------
# Square app icon
# ---------------------------------------------------------------------------
def make_icon():
    S = 256
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # rounded badge
    d.rounded_rectangle([8, 8, S - 8, S - 8], radius=46, fill=DEEP + (255,),
                        outline=CYAN + (255,), width=8)
    # checkered flag band across the top-third
    _checker(d, 24, 40, cols=8, rows=3, cell=26)

    # bold speed chevrons
    for i in range(3):
        xx = 60 + i * 44
        d.polygon([(xx, 150), (xx + 40, 190), (xx, 230), (xx + 16, 190)],
                  fill=(CYAN[0], CYAN[1], CYAN[2], 255 - i * 40))

    # red accent underline
    d.rectangle([40, 236, S - 40, 244], fill=RED + (255,))

    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(os.path.join(ASSETS, "icon.ico"), sizes=sizes)
    img.save(os.path.join(ASSETS, "icon.png"))
    print("wrote assets/icon.ico + icon.png")


if __name__ == "__main__":
    make_logo()
    make_icon()
