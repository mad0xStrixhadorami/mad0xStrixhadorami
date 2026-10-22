#!/usr/bin/env python3
"""Place an animated GIF inside an original handheld-device frame.

Usage:
    python make_device_frame.py input.gif output.gif

Requires: pip install pillow
"""
import sys
from PIL import Image, ImageDraw, ImageSequence

SS = 4                       # supersampling factor for smooth shapes
W, H = 560, 360              # final canvas size
SCREEN = (88, 52, 472, 244)  # screen box (x0, y0, x1, y1) -> 384x192 (2:1)

ACCENT = (0, 190, 170)
ACCENT_DARK = (0, 120, 108)


def S(v):
    return int(round(v * SS))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(w, h, top, bottom):
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        px[0, y] = lerp(top, bottom, y / max(h - 1, 1))
    return col.resize((w, h))


def chamfer(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c),
            (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def fill_shape(img, draw_mask, bbox, top, bottom):
    """Fill a shape with a vertical gradient. draw_mask(ImageDraw) draws it in white."""
    mask = Image.new("L", img.size, 0)
    draw_mask(ImageDraw.Draw(mask))
    x0, y0, x1, y1 = [S(v) for v in bbox]
    grad = gradient(x1 - x0, y1 - y0, top, bottom)
    layer = Image.new("RGB", img.size)
    layer.paste(grad, (x0, y0))
    img.paste(layer, (0, 0), mask)


def circle(img, cx, cy, r, top, bottom):
    fill_shape(img,
               lambda d: d.ellipse((S(cx - r), S(cy - r), S(cx + r), S(cy + r)), fill=255),
               (cx - r, cy - r, cx + r, cy + r), top, bottom)


def pill(img, x0, y0, x1, y1, top, bottom):
    r = (y1 - y0) / 2
    fill_shape(img,
               lambda d: d.rounded_rectangle((S(x0), S(y0), S(x1), S(y1)), radius=S(r), fill=255),
               (x0, y0, x1, y1), top, bottom)


def build_frame():
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # outer shell
    poly = [(S(x), S(y)) for x, y in chamfer(4, 4, W - 4, H - 4, 44)]
    fill_shape(img, lambda m: m.polygon(poly, fill=255), (4, 4, W - 4, H - 4),
               (24, 27, 33), (10, 12, 15))
    # main body, lighter at top
    poly = [(S(x), S(y)) for x, y in chamfer(10, 10, W - 10, H - 10, 40)]
    fill_shape(img, lambda m: m.polygon(poly, fill=255), (10, 10, W - 10, H - 10),
               (70, 77, 90), (32, 36, 44))
    # bevel highlight (top) and shade (bottom)
    d.line([(S(52), S(13)), (S(W - 52), S(13))], fill=(112, 121, 138), width=S(2))
    d.line([(S(52), S(H - 13)), (S(W - 52), S(H - 13))], fill=(20, 22, 27), width=S(2))

    # accent strip + segment LEDs at the top
    pill(img, 190, 20, W - 190, 27, ACCENT, ACCENT_DARK)

    # grip ridges on both sides
    for i in range(6):
        y = 120 + i * 16
        d.rounded_rectangle((S(24), S(y), S(30), S(y + 9)), radius=S(3), fill=(24, 27, 33))
        d.rounded_rectangle((S(W - 30), S(y), S(W - 24), S(y + 9)), radius=S(3), fill=(24, 27, 33))

    # screen bezel with thin edge highlight
    x0, y0, x1, y1 = SCREEN
    d.rounded_rectangle((S(x0 - 19), S(y0 - 19), S(x1 + 19), S(y1 + 19)),
                        radius=S(16), fill=(58, 64, 77))
    d.rounded_rectangle((S(x0 - 17), S(y0 - 17), S(x1 + 17), S(y1 + 17)),
                        radius=S(14), fill=(8, 9, 11))

    # left cluster: four-button diamond on a dark ring
    cx, cy = 122, 302
    circle(img, cx, cy, 40, (20, 22, 27), (14, 16, 19))
    for dx, dy in ((0, -22), (0, 22), (-22, 0), (22, 0)):
        top, bot = ((ACCENT, ACCENT_DARK) if (dx, dy) == (0, -22)
                    else ((92, 100, 116), (52, 57, 68)))
        circle(img, cx + dx, cy + dy, 11, top, bot)

    # right cluster: two pill buttons
    pill(img, W - 215, 288, W - 155, 314, (92, 100, 116), (52, 57, 68))
    pill(img, W - 140, 288, W - 80, 314, ACCENT, ACCENT_DARK)

    # center-bottom: status LEDs and a speaker grille
    for i, x in enumerate((W / 2 - 26, W / 2, W / 2 + 26)):
        circle(img, x, 276, 4, ACCENT if i == 1 else (84, 91, 106),
               ACCENT_DARK if i == 1 else (46, 50, 60))
    for i in range(7):
        x = W / 2 - 36 + i * 12
        d.rounded_rectangle((S(x), S(296), S(x + 4), S(320)), radius=S(2), fill=(22, 25, 30))

    img = img.resize((W, H), Image.LANCZOS)
    # GIF only supports 1-bit transparency
    a = img.getchannel("A").point(lambda v: 255 if v > 127 else 0)
    img.putalpha(a)
    return img


def build_glass(sw, sh):
    """Subtle glass reflection + inner shadow laid over every animation frame."""
    g = Image.new("RGBA", (sw * SS, sh * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    d.polygon([(0, 0), (S(sw * 0.55), 0), (0, S(sh * 0.6))], fill=(255, 255, 255, 22))
    d.rectangle((0, 0, sw * SS - 1, sh * SS - 1), outline=(0, 0, 0, 90), width=S(3))
    return g.resize((sw, sh), Image.LANCZOS)


def main(src, dst):
    frame = build_frame()
    sw, sh = SCREEN[2] - SCREEN[0], SCREEN[3] - SCREEN[1]
    glass = build_glass(sw, sh)
    src_im = Image.open(src)
    frames, durations = [], []
    for f in ImageSequence.Iterator(src_im):
        screen = f.convert("RGBA").resize((sw, sh), Image.NEAREST)
        screen = Image.alpha_composite(screen, glass)
        canvas = frame.copy()
        canvas.paste(screen, (SCREEN[0], SCREEN[1]))
        frames.append(canvas)
        durations.append(f.info.get("duration", 100))

    final = []
    for rgba in frames:
        p = rgba.convert("P", palette=Image.ADAPTIVE, colors=255)
        mask = rgba.getchannel("A").point(lambda v: 255 if v == 0 else 0)
        p.paste(255, mask=mask)  # palette index 255 = transparent
        final.append(p)
    final[0].save(dst, save_all=True, append_images=final[1:], duration=durations,
                  loop=0, disposal=2, transparency=255, optimize=False)
    print(f"Saved {dst} ({len(final)} frames)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
