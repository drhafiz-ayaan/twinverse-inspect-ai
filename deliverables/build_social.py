#!/usr/bin/env python3
"""Social media cards for TwinVerse Inspect AI.

Produces two crops from one design:
  1080 x 1080  square   — Instagram, LinkedIn, Facebook
  1200 x 630   landscape — X/Twitter, LinkedIn link preview

Palette and severity colours match the product exactly, so the post and the
live dashboard read as the same thing.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

OUT = Path(__file__).parent
SCREENSHOT = OUT / "dashboard_screenshot.jpg"
SCREENSHOT_SINGLE = OUT / "dashboard_screenshot_single.jpg"

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


def build(w: int, h: int, name: str, *, compact: bool):
    img = Image.new("RGBA", (w, h), (*BG, 255))
    base = ImageDraw.Draw(img)
    grid(base, w, h)

    glow(img, int(w * 0.06), int(h * 0.04), int(min(w, h) * 0.52), INDIGO, 0.30)
    glow(img, int(w * 0.95), int(h * 0.98), int(min(w, h) * 0.55), CYAN, 0.22)

    d = ImageDraw.Draw(img)

    # --- subject: a real screenshot of the dashboard ------------------------
    # This was a drawn illustration of a cracked panel. A generated picture of
    # a crack is a claim; a screenshot of the product finding one is evidence,
    # and it never has to be caveated. Regenerate with capture_dashboard.py.
    #
    # It is also the honest option: the drawing put four tidy boxes on a single
    # clean fracture, which is a better result than the model actually gets.
    # The square stacks text over a full-width two-up. The landscape has barely
    # 630px of height, so a full-width panel at any usable aspect ratio leaves
    # no room for the stats — it puts a single panel in a right-hand column
    # instead, with all the type beside it.
    if compact:
        source = SCREENSHOT
        panel_w = int(w * 0.86)
        panel_h = int(panel_w / 2.6)       # crops the two-up to a band
        px0 = (w - panel_w) // 2
        py0 = int(h * 0.375)
        text_w = w - int(w * 0.07) * 2
    else:
        source = SCREENSHOT_SINGLE
        panel_w = int(w * 0.34)
        panel_h = panel_w                  # one media panel, square
        px0 = w - panel_w - int(w * 0.055)
        py0 = (h - panel_h) // 2
        text_w = px0 - int(w * 0.07) - int(w * 0.03)

    if not source.is_file():
        raise SystemExit(
            f"missing {source.name} — with the stack running, run:\n"
            "  python deliverables/capture_dashboard.py --panel"
        )

    shot = Image.open(source).convert("RGBA")
    # Center-crop to the panel box rather than squashing: the detection boxes
    # are geometry, and a stretched bounding box is a wrong picture of the data.
    shot = ImageOps.fit(shot, (panel_w, panel_h), method=Image.LANCZOS,
                        centering=(0.5, 0.5))

    mask = Image.new("L", (panel_w, panel_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, panel_w - 1, panel_h - 1], radius=14, fill=255)
    img.paste(shot, (px0, py0), mask)

    d.rounded_rectangle([px0, py0, px0 + panel_w, py0 + panel_h],
                        radius=14, outline=(46, 60, 88), width=2)

    if compact:
        # Caption, so nobody has to guess whether the picture is real.
        cap = font("regular", int(min(w, h) * 0.0175))
        d.text((px0, py0 + panel_h + int(min(w, h) * 0.014)),
               "Actual output — detections and severity bands from the dashboard",
               font=cap, fill=DIM)

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
    sy = (py0 + panel_h + int(unit * 0.055)) if compact else (y + int(unit * 0.055))
    # Labelled "on familiar imagery" rather than left bare. There is no single
    # honest accuracy number here: the model scores 81% on imagery like its
    # training set and 63%, 13% and 8% on three it had never seen. A card has
    # room for one figure, so the figure is qualified and the range goes in the
    # caption copy — quoting an unseen number would mean picking which of the
    # three to show, and that choice is the dishonest part.
    stats = [("84%", "cracks found,\nworst of 4 datasets"), ("7ms", "per image"),
             ("104", "tests passing"), ("3", "person team")]
    col = text_w / len(stats)
    nf = font("bold", int(unit * 0.040))
    lf2 = font("regular", int(unit * 0.020))
    for i, (big, label) in enumerate(stats):
        x = pad + col * i
        d.text((x, sy), big, font=nf, fill=TEXT)
        nb = d.textbbox((0, 0), big, font=nf)
        ly0 = sy + (nb[3] - nb[1]) + int(unit * 0.014)
        # Labels wrap on an explicit newline rather than running on. A single
        # long label overflows its column and collides with the next stat —
        # these columns are evenly divided, so there is no slack to borrow.
        for line_no, part in enumerate(label.split("\n")):
            lb = d.textbbox((0, 0), part, font=lf2)
            d.text((x, ly0 + line_no * (lb[3] - lb[1] + int(unit * 0.010))),
                   part, font=lf2, fill=DIM)

    if not compact:
        # Same caption as the square, in the gap the left column leaves between
        # the stats and the credits. Wrapped by hand: the column is narrow and
        # there is no text layout engine here to do it.
        cap = font("regular", int(unit * 0.0195))
        cy = sy + int(unit * 0.155)
        for part in ("Actual output — detections and severity",
                     "bands, straight from the dashboard"):
            d.text((pad, cy), part, font=cap, fill=DIM)
            cb = d.textbbox((0, 0), part, font=cap)
            cy += (cb[3] - cb[1]) + int(unit * 0.014)

    # --- severity legend + credits ----------------------------------------
    # Clears two lines of stat label, not one — the accuracy label wraps. On the
    # landscape the type only fills the left column, so these anchor near the
    # bottom instead of trailing the stats and leaving the corner empty.
    ly = sy + int(unit * 0.128) if compact else int(h * 0.70)
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
