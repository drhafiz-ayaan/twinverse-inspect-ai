#!/usr/bin/env python3
"""Social media cards for TwinVerse Inspect AI.

Produces two crops from one design:
  1080 x 1080  square   — Instagram, LinkedIn, Facebook
  1200 x 630   landscape — X/Twitter, LinkedIn link preview

Palette and severity colours match the product exactly, so the post and the
live dashboard read as the same thing.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent

BG = (7, 11, 20)
TEXT = (232, 238, 248)
MUTED = (159, 176, 204)
DIM = (100, 116, 139)
CYAN = (34, 211, 238)
INDIGO = (99, 102, 241)
VIOLET = (167, 139, 250)

SEV = [
    ("low", (16, 185, 129)),
    ("medium", (245, 158, 11)),
    ("high", (249, 115, 22)),
    ("critical", (244, 63, 94)),
]

FONT_DIR = "/usr/share/fonts/truetype"
CANDIDATES = {
    "bold": [f"{FONT_DIR}/dejavu/DejaVuSans-Bold.ttf",
             f"{FONT_DIR}/liberation/LiberationSans-Bold.ttf"],
    "regular": [f"{FONT_DIR}/dejavu/DejaVuSans.ttf",
                f"{FONT_DIR}/liberation/LiberationSans-Regular.ttf"],
}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in CANDIDATES[kind]:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def glow(img: Image.Image, cx: int, cy: int, radius: int, colour, alpha: float):
    """Soft radial glow, composited so edges stay genuinely soft.

    Drawing a flat translucent circle leaves a hard rim that reads as a shape
    rather than light; blurring the layer before compositing is what sells it.
    """
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
              fill=(*colour, int(255 * alpha)))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.42))
    img.alpha_composite(layer)


def grid(draw: ImageDraw.ImageDraw, w: int, h: int, step: int = 64):
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=(23, 35, 58), width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=(23, 35, 58), width=1)


def crack_path(rng: random.Random, x0, y0, x1, y1, jitter, steps=34):
    """A jagged polyline standing in for a crack.

    Perpendicular offsets rather than independent x/y jitter: a real fracture
    wanders *across* its direction of travel. Offsetting both axes freely
    produces the gentle rolling curve of a line chart instead.
    """
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length, dx / length   # unit normal
    pts = []
    drift = 0.0
    for i in range(steps + 1):
        t = i / steps
        # Random walk, not independent noise, so deviations persist and the
        # line looks like it is following a fault rather than oscillating.
        drift = drift * 0.62 + rng.uniform(-jitter, jitter)
        # Pinch to zero at both ends so the crack starts and stops naturally.
        taper = math.sin(math.pi * t) ** 0.5
        px = x0 + dx * t + nx * drift * taper
        py = y0 + dy * t + ny * drift * taper
        pts.append((px, py))
    return pts


def draw_crack(d: ImageDraw.ImageDraw, pts, max_width: float, colour):
    """Draw a polyline whose width tapers toward both ends."""
    n = len(pts) - 1
    for i in range(n):
        t = i / n
        w = max(1.0, max_width * (math.sin(math.pi * t) ** 0.6))
        shade = int(150 - 40 * abs(0.5 - t) * 2)
        d.line([pts[i], pts[i + 1]],
               fill=(shade, shade + 13, shade + 30), width=int(round(w)))


def build(w: int, h: int, name: str, *, compact: bool):
    img = Image.new("RGBA", (w, h), (*BG, 255))
    base = ImageDraw.Draw(img)
    grid(base, w, h)

    glow(img, int(w * 0.06), int(h * 0.04), int(min(w, h) * 0.52), INDIGO, 0.30)
    glow(img, int(w * 0.95), int(h * 0.98), int(min(w, h) * 0.55), CYAN, 0.22)

    d = ImageDraw.Draw(img)
    rng = random.Random(7)

    # --- subject: a concrete panel with a fracture and detection overlays --
    # Drawn as an inspection *photograph* rather than a bare line. A shallow
    # diagonal with boxes on it reads as a trend chart no matter how jagged it
    # is; a textured panel with a steep fracture reads as concrete.
    panel_w = int(w * 0.86)
    panel_h = int(h * (0.30 if compact else 0.31))
    px0 = (w - panel_w) // 2
    py0 = int(h * (0.40 if compact else 0.375))

    panel = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([0, 0, panel_w - 1, panel_h - 1], radius=14,
                         fill=(31, 38, 50, 255))

    # Concrete speckle — enough texture to read as a surface, not a swatch.
    for _ in range(int(panel_w * panel_h / 210)):
        sx = rng.randrange(panel_w)
        sy = rng.randrange(panel_h)
        v = rng.randint(-16, 20)
        r = rng.choice((1, 1, 1, 2))
        pd.ellipse([sx, sy, sx + r, sy + r],
                   fill=(46 + v, 53 + v, 66 + v, 255))

    # Steep fracture: near-vertical is unmistakably a crack.
    main = crack_path(rng, panel_w * 0.30, -6,
                      panel_w * 0.62, panel_h + 6,
                      jitter=panel_h * 0.085, steps=40)
    draw_crack(pd, main, max_width=max(4, w / 210), colour=None)
    for anchor, dx_f, dy_f in ((12, 0.20, 0.20), (26, -0.16, 0.17), (32, 0.13, 0.12)):
        ax, ay = main[anchor]
        b = crack_path(rng, ax, ay, ax + panel_w * dx_f, ay + panel_h * dy_f,
                       jitter=panel_h * 0.05, steps=16)
        draw_crack(pd, b, max_width=max(2, w / 430), colour=None)

    # Rounded-corner mask so the texture cannot spill past the panel edge.
    mask = Image.new("L", (panel_w, panel_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, panel_w - 1, panel_h - 1], radius=14, fill=255)
    img.paste(panel, (px0, py0), mask)

    d.rounded_rectangle([px0, py0, px0 + panel_w, py0 + panel_h],
                        radius=14, outline=(46, 60, 88), width=2)

    # Detection boxes, tracking the fracture, in the dashboard's own colours.
    boxes = [
        ("critical", 0.02, 0.30, 0.30),
        ("high",     0.33, 0.26, 0.26),
        ("medium",   0.60, 0.24, 0.22),
        ("low",      0.82, 0.16, 0.16),
    ]
    lf = font("bold", max(11, w // 80))
    for band, fy, fh, fw in boxes:
        colour = dict(SEV)[band]
        idx = min(len(main) - 1, int((fy + fh / 2) * len(main)))
        cx = px0 + main[idx][0]
        by = py0 + panel_h * fy
        bh = panel_h * fh
        bw = panel_w * fw
        bx = max(px0 + 8, min(cx - bw / 2, px0 + panel_w - bw - 8))
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=5,
                            outline=colour, width=max(2, w // 430))
        label = band.upper()
        tw = d.textlength(label, font=lf)
        d.rounded_rectangle([bx, by - (h // 48), bx + tw + 13, by - 2],
                            radius=4, fill=colour)
        d.text((bx + 6, by - (h // 48) + 2), label, font=lf, fill=(10, 14, 22))

    # --- wordmark ---------------------------------------------------------
    # Fonts scale with the SHORTER side and vertical positions advance by
    # measured line height. Sizing type by width while spacing by height
    # collapses the moment the aspect ratio changes — at 1200x630 the title,
    # tagline and body all landed on top of one another.
    unit = min(w, h)
    pad = int(w * 0.07)

    def line(text, f, fill, y, gap):
        d.text((pad, y), text, font=f, fill=fill)
        bbox = d.textbbox((0, 0), text, font=f)
        return y + (bbox[3] - bbox[1]) + gap

    y = int(h * 0.075)
    y = line("A U T O N O M O U S   S T R U C T U R A L   S C R E E N I N G",
             font("bold", max(11, int(unit * 0.0165))), CYAN, y, int(unit * 0.038))
    y = line("TwinVerse Inspect AI",
             font("bold", int(unit * 0.072)), TEXT, y, int(unit * 0.030))
    y = line("Inspect the unreachable.",
             font("regular", int(unit * 0.042)), CYAN, y, int(unit * 0.030))

    bf = font("regular", int(unit * 0.0225))
    y = line("AI that finds structural cracks from a photograph,", bf, MUTED,
             y, int(unit * 0.012))
    y = line("ranks them by severity, and shows its working.", bf, MUTED,
             y, int(unit * 0.02))

    # --- stats strip -------------------------------------------------------
    sy = py0 + panel_h + int(unit * 0.055)
    stats = [("81%", "of cracks found"), ("7ms", "per image"),
             ("101", "tests passing"), ("3", "person team")]
    col = (w - pad * 2) / len(stats)
    nf = font("bold", int(unit * 0.040))
    lf2 = font("regular", int(unit * 0.020))
    for i, (big, label) in enumerate(stats):
        x = pad + col * i
        d.text((x, sy), big, font=nf, fill=TEXT)
        nb = d.textbbox((0, 0), big, font=nf)
        d.text((x, sy + (nb[3] - nb[1]) + int(unit * 0.014)), label,
               font=lf2, fill=DIM)

    # --- severity legend + credits ----------------------------------------
    ly = sy + int(unit * 0.105)
    x = pad
    lf3 = font("regular", int(unit * 0.019))
    for band, colour in SEV:
        d.ellipse([x, ly + int(unit * 0.004), x + int(unit * 0.011),
                   ly + int(unit * 0.015)], fill=colour)
        d.text((x + int(unit * 0.019), ly), band, font=lf3, fill=MUTED)
        x += int(d.textlength(band, font=lf3)) + int(unit * 0.062)

    cf = font("bold", int(unit * 0.0215))
    d.text((pad, ly + int(unit * 0.052)),
           "Ayaan Aatif  ·  Muhammad Muneed  ·  Inshrah Mehmood",
           font=cf, fill=MUTED)

    out = OUT / name
    img.convert("RGB").save(out, quality=94)
    print(f"wrote {out}  ({w}x{h})")


if __name__ == "__main__":
    build(1080, 1080, "social_square_1080.jpg", compact=True)
    build(1200, 630, "social_landscape_1200x630.jpg", compact=False)
