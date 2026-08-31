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


def main() -> int:
    email = env_value("BOOTSTRAP_ADMIN_EMAIL")
    password = env_value("BOOTSTRAP_ADMIN_PASSWORD")
    if not (email and password):
        sys.exit("set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD in backend/.env")
    if not IMAGE_DIR.is_dir():
        sys.exit(f"no imagery at {IMAGE_DIR}")

    files = sorted(IMAGE_DIR.glob("*.jpg"))[:UPLOAD_COUNT]
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
        beat(page, 2600)

        # The scoring model, before anything is claimed about a score. This is
        # the differentiator and it costs six seconds.
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
        beat(page, 1400)

        page.locator("#title").click()
        page.locator("#title").type("North span deck survey", delay=55)
        beat(page, 700)

        # "+ Create a new asset" is the last option in the select.
        page.select_option("#asset", "new")
        beat(page, 900)
        page.locator("#asset-name").type("Riverside Viaduct", delay=55)
        page.locator("#asset-location").type("Sector 7, North Span", delay=45)
        beat(page, 900)

        page.locator("#files").set_input_files([str(f) for f in files])
        beat(page, 1600)

        # --- 3. the pipeline, running ---------------------------------------
        page.get_by_role("button", name="Upload and analyse").click()
        # Detection is real work; this wait is the honest length of it.
        page.wait_for_url("**/inspections/**", timeout=180_000)
        page.wait_for_load_state("networkidle")
        scrub_identity()
        beat(page, 2600)

        # --- 4. the findings -------------------------------------------------
        glide(page, 320)
        beat(page, 2400)          # severity distribution
        glide(page, 760)
        beat(page, 2600)          # highest-severity table, with the arithmetic

        # --- 5. a detection, on the photograph ------------------------------
        panel = page.locator("div.grid.gap-4.md\\:grid-cols-2 > div").first
        panel.scroll_into_view_if_needed()
        beat(page, 1500)
        rows = panel.locator("button")
        for i in range(min(4, rows.count())):
            rows.nth(i).hover()
            beat(page, 1400)      # each hover lights its box on the image

        # --- 6. the 3D view --------------------------------------------------
        canvas = page.locator("canvas").first
        if canvas.count():
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
        beat(page, 1200)
        page.get_by_role("link", name="Download PDF report").hover()
        beat(page, 2200)

        context.close()          # flushes the video file
        browser.close()

    raw = next(raw_dir.glob("*.webm"), None)
    if raw is None:
        sys.exit("playwright produced no video")

    webm = HERE / "demo_backup.webm"
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
        subprocess.run(
            [ffmpeg, "-y", "-i", str(webm),
             "-c:v", "libx264", "-preset", "slow", "-crf", "20",
             # yuv420p and even dimensions: QuickTime and most phones reject
             # anything else, which is exactly when a backup gets used.
             "-pix_fmt", "yuv420p",
             "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
             "-movflags", "+faststart",
             str(OUT_MP4)],
            check=True, capture_output=True,
        )
        print(f"wrote {OUT_MP4}  ({OUT_MP4.stat().st_size / 1e6:.1f} MB)")
    else:
        print("ffmpeg not found — keeping webm only")

    print(f"wrote {webm}  ({webm.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
