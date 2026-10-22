#!/usr/bin/env python3
"""Place an animated GIF inside a handheld-device frame.

Usage:
    python make_device_frame.py input.gif output.gif

Requires: pip install pillow
"""
import sys
from PIL import Image, ImageDraw, ImageSequence

SS = 4                      # supersampling factor for smooth shapes
W, H = 560, 360             # final canvas size
SCREEN = (88, 52, 472, 244) # screen box (x0, y0, x1, y1) -> 384x192 (2:1)

BODY = (38, 42, 50)
BODY_EDGE = (22, 25, 30)
ACCENT = (0, 190, 170)
BEZEL = (12, 13, 16)
BTN = (58, 63, 74)
BTN_EDGE = (28, 31, 37)


def build_frame():
    w, h = W * SS, H * SS
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = lambda v: int(v * SS)

    # body
    d.rounded_rectangle((s(6), s(6), s(W - 6), s(H - 6)), radius=s(46), fill=BODY_EDGE)
    d.rounded_rectangle((s(12), s(12), s(W - 12), s(H - 12)), radius=s(42), fill=BODY)
    # accent strip along the top
    d.rounded_rectangle((s(150), s(20), s(W - 150), s(26)), radius=s(3), fill=ACCENT)

    # screen bezel
    x0, y0, x1, y1 = SCREEN
    d.rounded_rectangle((s(x0 - 16), s(y0 - 16), s(x1 + 16), s(y1 + 16)),
                        radius=s(14), fill=BEZEL)

    # d-pad (bottom left)
    cx, cy = 130, 296
    d.ellipse((s(cx - 40), s(cy - 40), s(cx + 40), s(cy + 40)), fill=BTN_EDGE)
    d.ellipse((s(cx - 36), s(cy - 36), s(cx + 36), s(cy + 36)), fill=BTN)
    d.ellipse((s(cx - 12), s(cy - 12), s(cx + 12), s(cy + 12)), fill=BTN_EDGE)
    for dx, dy in ((0, -24), (0, 24), (-24, 0), (24, 0)):
        d.ellipse((s(cx + dx - 3), s(cy + dy - 3), s(cx + dx + 3), s(cy + dy + 3)), fill=ACCENT)

    # action buttons (bottom right)
    for bx, by, col in ((W - 160, 296, ACCENT), (W - 100, 276, BTN)):
        d.ellipse((s(bx - 22), s(by - 22), s(bx + 22), s(by + 22)), fill=BTN_EDGE)
        d.ellipse((s(bx - 18), s(by - 18), s(bx + 18), s(by + 18)), fill=col)

    img = img.resize((W, H), Image.LANCZOS)
    # GIF only supports 1-bit transparency: remove half-transparent edge pixels
    a = img.getchannel("A").point(lambda v: 255 if v > 127 else 0)
    img.putalpha(a)
    return img


def main(src, dst):
    frame = build_frame()
    sw, sh = SCREEN[2] - SCREEN[0], SCREEN[3] - SCREEN[1]
    src_im = Image.open(src)
    frames, durations = [], []
    for f in ImageSequence.Iterator(src_im):
        screen = f.convert("RGBA").resize((sw, sh), Image.NEAREST)
        canvas = frame.copy()
        canvas.paste(screen, (SCREEN[0], SCREEN[1]))
        frames.append(canvas)
        durations.append(f.info.get("duration", 100))

    out = [fr.convert("P", palette=Image.ADAPTIVE, colors=255) for fr in frames]
    # reserve palette index 255 for transparency
    final = []
    for fr, rgba in zip(out, frames):
        mask = rgba.getchannel("A").point(lambda v: 255 if v == 0 else 0)
        fr.paste(255, mask=mask)
        final.append(fr)
    final[0].save(dst, save_all=True, append_images=final[1:], duration=durations,
                  loop=0, disposal=2, transparency=255, optimize=False)
    print(f"Saved {dst} ({len(final)} frames)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
