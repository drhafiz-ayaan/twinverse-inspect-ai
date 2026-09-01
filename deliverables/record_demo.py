#!/usr/bin/env python3
"""Record the backup demo video.

Live demos fail. This drives the real stack through the whole pitch — create
an inspection, upload imagery, watch detection run, read the severity
arithmetic, orbit the 3D view — and records it, so there is something to play
when the wifi dies or the laptop refuses to wake up.

Nothing is faked: every frame is the actual application doing the actual work,
including the wait while inference runs.

    python deliverables/record_demo.py

Requires the stack running and `playwright` installed. Uses the system Chrome.
Writes demo_backup.mp4 (and keeps the raw .webm if ffmpeg is unavailable).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture_dashboard import DASHBOARD, env_value  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
IMAGE_DIR = REPO_ROOT / "ml" / "datasets" / "nitw-crack" / "test" / "images"
OUT_MP4 = HERE / "demo_backup.mp4"

VIEWPORT = {"width": 1280, "height": 720}
UPLOAD_COUNT = 6

# The short cut is a different film, not a trim of the long one. A 70-second
# recording contains ~15 seconds of genuine inference; you cannot cut that out
# without either lying about the wait or leaving nothing else. So it uploads
# fewer images, holds every beat for less time, and drops the 3D viewer and the
# report — on a muted autoplaying feed those read as filler.
SHORT_UPLOAD_COUNT = 3


def beat(page, ms: int) -> None:
    """A deliberate pause. The viewer needs time to read what is on screen."""
    page.wait_for_timeout(ms)


def glide(page, to: int, steps: int = 26) -> None:
    """Scroll smoothly to an absolute offset.

    Playwright's scrolling jumps, which on video looks like a cut rather than a
    camera move. Stepping it manually keeps the eye anchored.
    """
    current = page.evaluate("window.scrollY")
    for i in range(1, steps + 1):
        page.evaluate(f"window.scrollTo(0, {current + (to - current) * i / steps})")
        page.wait_for_timeout(22)


def _render_social(ffmpeg: str, webm: Path, out: Path, speed: float,
                   tail_seconds: float, *, square: bool) -> None:
    """Compose one social aspect: magnified screen recording plus chrome.

    Square (1:1) crops the magnified recording edge to edge. Vertical (9:16)
    cannot: a 16:9 desktop UI in a 9:16 frame leaves two thirds of the height
    empty, so the same square crop is inset into a taller canvas and the space
    above and below carries the wordmark and the numbers. That is a layout, not
    letterboxing — the empty bars are doing work.
    """
    W, H = (1080, 1080) if square else (1080, 1920)
    inset_y = 0 if square else 430

    chrome = _make_chrome(out.with_name(f"_chrome_{W}x{H}.png"), W, H, inset_y, square)
    end_card = _make_end_card(out.with_name(f"_end_{W}x{H}.png"), W, H)
    body = out.with_name(f"_body_{W}x{H}.mp4")
    tail = out.with_name(f"_tail_{W}x{H}.mp4")
    listing = out.with_name(f"_concat_{W}x{H}.txt")

    # Magnify and crop rather than letterbox. Fitting 1280x720 into 1080 wide
    # leaves the UI unreadable on a phone; scaling to 1080 tall and cropping
    # 1080 wide gives 1.5x on the content column. The x offset keeps that column
    # in frame — the dashboard content sits left of centre in a max-width
    # container, so a centred crop clipped the headline.
    crop = f"setpts=PTS/{speed:.4f},scale=-2:1080,crop=1080:1080:36:0"
    graph = (f"[0:v]{crop}[v];"
             f"color=c=0x070B14:s={W}x{H}[bg];"
             f"[bg][v]overlay=0:{inset_y}:shortest=1[framed];"
             f"[framed][1:v]overlay=0:0[out]")

    subprocess.run(
        [ffmpeg, "-y", "-i", str(webm), "-i", str(chrome),
         "-filter_complex", graph, "-map", "[out]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "20",
         "-pix_fmt", "yuv420p", "-r", "25", str(body)],
        check=True, capture_output=True,
    )
    subprocess.run(
        [ffmpeg, "-y", "-loop", "1", "-t", str(tail_seconds), "-i", str(end_card),
         "-c:v", "libx264", "-preset", "slow", "-crf", "20",
         "-pix_fmt", "yuv420p", "-r", "25", "-vf", f"scale={W}:{H}", str(tail)],
        check=True, capture_output=True,
    )
    # Concat demuxer refuses streams that differ, so both were encoded with
    # identical parameters above.
    listing.write_text(f"file '{body.name}'\nfile '{tail.name}'\n")
    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c", "copy", "-movflags", "+faststart", str(out)],
        check=True, capture_output=True, cwd=str(out.parent),
    )
    for tmp in (body, tail, listing, chrome, end_card):
        tmp.unlink(missing_ok=True)


def _duration(ffmpeg: str, path: Path) -> float:
    """Seconds, parsed from ffmpeg's own report — ffprobe is not bundled."""
    import re
    out = subprocess.run([ffmpeg, "-i", str(path)],
                         capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    if not m:
        return 0.0
    h, mnt, sec = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(sec)


BG = (7, 11, 20)
TEXT = (232, 238, 248)
MUTED = (159, 176, 204)
CYAN = (34, 211, 238)
FONTS = {
    "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
}


def _font(kind: str, size: int):
    from PIL import ImageFont
    path = FONTS[kind]
    return ImageFont.truetype(path, size) if Path(path).is_file() \
        else ImageFont.load_default()


def _make_chrome(path: Path, w: int, h: int, inset_y: int, square: bool) -> Path:
    """Wordmark and supporting text, composited over the framed recording.

    Social autoplays muted, so the frame has to say what it is without a
    caption. On the square this is a band across the top of live UI; on the
    vertical there is real space above and below the video, so the same
    information can breathe and the numbers go in the footer.
    """
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if square:
        # Laid over live UI, so it needs an opaque band or it is unreadable
        # half the time.
        d.rectangle([0, 0, w, 104], fill=(*BG, 236))
        d.text((40, 22), "TwinVerse Inspect AI", font=_font("bold", 36), fill=(*TEXT, 255))
        d.text((40, 66), "Finds structural cracks from a photograph.",
               font=_font("regular", 23), fill=(*CYAN, 255))
        return img.save(path) or path

    # --- vertical: header above the video, numbers below --------------------
    d.text((64, 150), "A U T O N O M O U S   S C R E E N I N G",
           font=_font("bold", 22), fill=(*CYAN, 255))
    d.text((64, 200), "TwinVerse", font=_font("bold", 76), fill=(*TEXT, 255))
    d.text((64, 284), "Inspect AI", font=_font("bold", 76), fill=(*CYAN, 255))
    d.text((64, 386), "Finds structural cracks from a photograph.",
           font=_font("regular", 30), fill=(*MUTED, 255))

    foot = inset_y + 1080 + 70
    d.text((64, foot), "Every severity score shows its own arithmetic.",
           font=_font("bold", 32), fill=(*TEXT, 255))
    # The worst of four datasets, matching the printed cards. A vertical clip
    # is the easiest place to quietly quote the best one instead.
    d.text((64, foot + 58), "84% of cracks found — worst of four datasets",
           font=_font("regular", 27), fill=(*MUTED, 255))

    x = 64
    for label, colour in (("low", (16, 185, 129)), ("medium", (245, 158, 11)),
                          ("high", (249, 115, 22)), ("critical", (244, 63, 94))):
        d.ellipse([x, foot + 132, x + 16, foot + 148], fill=(*colour, 255))
        d.text((x + 28, foot + 126), label, font=_font("regular", 25),
               fill=(*MUTED, 255))
        x += int(d.textlength(label, font=_font("regular", 25))) + 92

    d.text((64, foot + 200), "Ayaan Aatif · Muhammad Muneed · Inshrah Mehmood",
           font=_font("bold", 26), fill=(*MUTED, 255))
    img.save(path)
    return path


def _make_end_card(path: Path, w: int = 1080, h: int = 1080) -> Path:
    """Closing frame. Anchored to the frame centre so one layout serves both
    the 1:1 and the 9:16 crop."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    top = h // 2 - 240
    d.text((70, top), "TwinVerse", font=_font("bold", 78), fill=TEXT)
    d.text((70, top + 86), "Inspect AI", font=_font("bold", 78), fill=CYAN)
    d.text((70, top + 212), "Inspect the unreachable.",
           font=_font("regular", 34), fill=MUTED)
    # The worst of four datasets, matching the printed cards. A short clip is
    # the easiest place to quietly quote the flattering number instead.
    d.text((70, top + 304), "84% of cracks found — worst of four datasets",
           font=_font("regular", 25), fill=MUTED)
    d.text((70, top + 346), "Every severity score shows its own arithmetic",
           font=_font("regular", 25), fill=MUTED)
    d.text((70, top + 530), "Ayaan Aatif  ·  Muhammad Muneed  ·  Inshrah Mehmood",
           font=_font("bold", 26), fill=MUTED)
    img.save(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--short", action="store_true",
                        help="Record the ~30s social cut and render it square")
    args = parser.parse_args()
    short = args.short

    email = env_value("BOOTSTRAP_ADMIN_EMAIL")
    password = env_value("BOOTSTRAP_ADMIN_PASSWORD")
    if not (email and password):
        sys.exit("set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD in backend/.env")
    if not IMAGE_DIR.is_dir():
        sys.exit(f"no imagery at {IMAGE_DIR}")

    count = SHORT_UPLOAD_COUNT if short else UPLOAD_COUNT
    files = sorted(IMAGE_DIR.glob("*.jpg"))[:count]
    out_mp4 = HERE / ("demo_social_30s.mp4" if short else "demo_backup.mp4")
    raw_dir = HERE / "_video_raw"
    shutil.rmtree(raw_dir, ignore_errors=True)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        context = browser.new_context(
            viewport=VIEWPORT,
            color_scheme="dark",
            record_video_dir=str(raw_dir),
            record_video_size=VIEWPORT,
        )
        resp = context.request.post(
            f"{DASHBOARD}/api/session",
            data={"email": email, "password": password},
        )
        if not resp.ok:
            sys.exit(f"session route rejected the credentials ({resp.status})")

        page = context.new_page()

        def scrub_identity() -> None:
            """Blank the signed-in address. The video is meant to be shared."""
            page.add_style_tag(content="nextjs-portal { display: none !important; }")
            page.evaluate("""() => {
                const hits = document.evaluate(
                    "//*[contains(text(), '@')]", document, null,
                    XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
                for (let i = 0; i < hits.snapshotLength; i++) {
                    const el = hits.snapshotItem(i);
                    if (!el.children.length && /@[\\w.-]+\\.\\w+/.test(el.textContent)) {
                        el.textContent = "inspector@twinverse.ai";
                    }
                }
            }""")

        # --- 1. the dashboard ------------------------------------------------
        page.goto(DASHBOARD, wait_until="networkidle", timeout=60_000)
        scrub_identity()
        beat(page, 2600 if not short else 1200)

        if not short:
            # The scoring model, before anything is claimed about a score. This
            # is the differentiator and it costs six seconds. The short cut
            # cannot afford it — a feed viewer will not read a formula.
            glide(page, 900)
            beat(page, 3200)
            glide(page, 0)
            beat(page, 900)

        # --- 2. start an inspection -----------------------------------------
        page.get_by_role("button", name="+ New inspection").click()
        # The panel mounts client-side; assert it rather than assuming, so a
        # slow mount fails here with a clear message instead of 30s later on a
        # field that was never going to exist.
        page.wait_for_selector("#title", timeout=20_000)
        beat(page, 700 if short else 1400)

        page.locator("#title").click()
        page.locator("#title").type("North span deck survey", delay=25 if short else 55)
        beat(page, 400 if short else 700)

        # "+ Create a new asset" is the last option in the select.
        page.select_option("#asset", "new")
        beat(page, 400 if short else 900)
        page.locator("#asset-name").type("Riverside Viaduct", delay=25 if short else 55)
        if not short:
            page.locator("#asset-location").type("Sector 7, North Span", delay=45)
        beat(page, 400 if short else 900)

        page.locator("#files").set_input_files([str(f) for f in files])
        beat(page, 900 if short else 1600)

        # --- 3. the pipeline, running ---------------------------------------
        page.get_by_role("button", name="Upload and analyse").click()
        # Detection is real work; this wait is the honest length of it.
        page.wait_for_url("**/inspections/**", timeout=180_000)
        page.wait_for_load_state("networkidle")
        scrub_identity()
        beat(page, 1600 if short else 2600)

        # --- 4. the findings -------------------------------------------------
        glide(page, 320)
        beat(page, 2200 if short else 2400)   # severity distribution
        if not short:
            glide(page, 760)
            beat(page, 2600)      # highest-severity table, with the arithmetic

        # --- 5. a detection, on the photograph ------------------------------
        panel = page.locator("div.grid.gap-4.md\\:grid-cols-2 > div").first
        panel.scroll_into_view_if_needed()
        beat(page, 1500)
        rows = panel.locator("button")
        for i in range(min(2 if short else 4, rows.count())):
            rows.nth(i).hover()
            beat(page, 1200 if short else 1400)  # hover lights its box

        # --- 6. the 3D view --------------------------------------------------
        # Dropped from the short cut: it is the most heavily caveated feature,
        # and giving it screen time in a 30-second clip misrepresents the
        # product's balance.
        canvas = page.locator("canvas").first
        if not short and canvas.count():
            canvas.scroll_into_view_if_needed()
            beat(page, 1800)
            box = canvas.bounding_box()
            if box:
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                page.mouse.move(cx, cy)
                page.mouse.down()
                # Few steps deliberately. Each mouse.move is a round trip to the
                # browser costing a couple of hundred milliseconds, so a 68-step
                # orbit ran for nearly half a minute and gave the most heavily
                # caveated feature more screen time than the detections.
                for i in range(14):
                    page.mouse.move(cx + 190 * (i / 14), cy - 40 * (i / 14))
                for i in range(14):
                    page.mouse.move(cx + 190 - 300 * (i / 14), cy - 40 + 30 * (i / 14))
                page.mouse.up()
                beat(page, 1400)

        # --- 7. the report ---------------------------------------------------
        glide(page, 0)
        beat(page, 900 if short else 1200)
        page.get_by_role("link", name="Download PDF report").hover()
        beat(page, 1600 if short else 2200)

        context.close()          # flushes the video file
        browser.close()

    raw = next(raw_dir.glob("*.webm"), None)
    if raw is None:
        sys.exit("playwright produced no video")

    webm = out_mp4.with_suffix(".webm")
    shutil.move(str(raw), webm)
    shutil.rmtree(raw_dir, ignore_errors=True)

    # H.264 mp4 as well: webm plays in browsers but several presentation tools
    # and phones will not touch it, and a backup video that will not open is
    # not a backup.
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        ffmpeg = get_ffmpeg_exe()
    except Exception:
        ffmpeg = shutil.which("ffmpeg")

    if ffmpeg:
        if short:
            # Land on 30 seconds. The raw run varies by a few seconds because
            # real inference does, so the speed-up is computed from the measured
            # duration rather than hardcoded — and it is often 1.00x, leaving
            # the timing untouched. The full-length recording always keeps the
            # honest timing, including the unedited inference wait.
            TARGET, TAIL = 30.0, 2.5
            measured = _duration(ffmpeg, webm)
            speed = max(1.0, measured / (TARGET - TAIL)) if measured else 1.0
            print(f"  raw {measured:.1f}s -> {speed:.2f}x to hit {TARGET:.0f}s")

            # Both aspects come from the same recording. Rendering them from
            # separate runs would let the square and the vertical drift apart —
            # different detections, different counts, same claimed product.
            _render_social(ffmpeg, webm, out_mp4, speed, TAIL, square=True)
            vertical = out_mp4.with_name("demo_social_30s_vertical.mp4")
            _render_social(ffmpeg, webm, vertical, speed, TAIL, square=False)
            print(f"wrote {vertical}  ({vertical.stat().st_size / 1e6:.1f} MB)")
        else:
            subprocess.run(
                [ffmpeg, "-y", "-i", str(webm),
                 "-c:v", "libx264", "-preset", "slow", "-crf", "20",
                 # yuv420p and even dimensions: QuickTime and most phones reject
                 # anything else, which is exactly when a backup gets used.
                 "-pix_fmt", "yuv420p",
                 "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                 "-movflags", "+faststart",
                 str(out_mp4)],
                check=True, capture_output=True,
            )
        print(f"wrote {out_mp4}  ({out_mp4.stat().st_size / 1e6:.1f} MB)")
    else:
        print("ffmpeg not found — keeping webm only")

    print(f"wrote {webm}  ({webm.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
