#!/usr/bin/env python3
"""Screenshot the running dashboard for use in the social cards.

The card previously carried a drawn illustration of a cracked panel. A real
screenshot is better on every axis — it is the actual product, and a wide short
panel made the drawn fracture read as a declining line chart.

Authentication is done the way demo.sh does it: credentials are read from
backend/.env and posted to the dashboard's own session route, which sets the
httpOnly cookie on the browser context. Nothing is typed into a form and the
password is never printed.

    python deliverables/capture_dashboard.py [--inspection <id>]

Requires the stack to be running and `playwright` installed. Uses the system
Chrome (channel="chrome") rather than downloading a browser.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "backend" / ".env"
OUT = Path(__file__).parent / "dashboard_screenshot.jpg"

DASHBOARD = "http://localhost:3000"
API = "http://localhost:8000/api/v1"

# Wide enough that the media panel sits beside the summary rather than under it,
# which is the layout worth showing.
VIEWPORT = {"width": 1500, "height": 1000}


def env_value(key: str) -> str | None:
    """Read one key from backend/.env.

    Parsed rather than sourced: the file is not shell, and MODEL_WEIGHTS holds
    an unquoted path with a space in it.
    """
    if not ENV_FILE.is_file():
        return None
    value = None
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith(f"{key}="):
            value = line[len(key) + 1:].strip()
    if value and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value or None


def api_json(path: str, token: str):
    req = urllib.request.Request(
        f"{API}{path}", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def login(email: str, password: str) -> str:
    body = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{API}/auth/login", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)["access_token"]


def busiest_inspection(token: str) -> str:
    """The completed inspection with the most detections makes the best image."""
    inspections = api_json("/inspections", token)
    best, best_count = None, -1
    for insp in inspections:
        if insp["status"] != "completed":
            continue
        summary = api_json(f"/inspections/{insp['id']}/detections/summary", token)
        if summary["detection_total"] > best_count:
            best, best_count = insp["id"], summary["detection_total"]
    if best is None:
        sys.exit("no completed inspection to photograph — run ./demo.sh first")
    print(f"  using inspection {best}  ({best_count} detections)")
    return best


IMAGE_CELL = "div.grid.gap-4.md\\:grid-cols-2 > div > div.relative"


def pick_panels(page, out: Path) -> None:
    """Screenshot individual detection panels and keep the two most photographic.

    Each panel is captured as its own element rather than by slicing one tall
    screenshot into a grid. Cards are not a uniform height — the detail list
    under each image varies with the number of detections — so fixed row
    arithmetic drifts, and the sticky page header overlays whatever it is
    scrolled past. Both showed up as garbage in the composed panel.

    The inspection also mixes ordinary photographs with near-white contrast
    scans and some very dark frames. Those are real detections, but on a card
    they read as a broken image, so panels are scored and the most textured
    mid-tone two are chosen.
    """
    from io import BytesIO

    from PIL import Image, ImageStat

    cells = page.locator(IMAGE_CELL)
    total = min(cells.count(), 16)
    scored = []
    for i in range(total):
        cell = cells.nth(i)
        cell.scroll_into_view_if_needed()
        page.wait_for_timeout(120)
        shot = Image.open(BytesIO(cell.screenshot())).convert("RGB")
        stat = ImageStat.Stat(shot.convert("L"))
        mean, spread = stat.mean[0], stat.stddev[0]
        if 90 <= mean <= 205 and spread >= 35:
            scored.append((spread, shot))

    if len(scored) < 2:
        sys.exit(f"only {len(scored)} usable detection panels in {total} cards")

    scored.sort(key=lambda s: -s[0])
    left, right = scored[0][1], scored[1][1]

    # Match heights before pasting; panels differ by a pixel or two.
    height = min(left.height, right.height)
    left = left.crop((0, 0, left.width, height))
    right = right.crop((0, 0, right.width, height))

    gap = 24
    panel = Image.new("RGB", (left.width + gap + right.width, height), (7, 11, 20))
    panel.paste(left, (0, 0))
    panel.paste(right, (left.width + gap, 0))
    panel.save(out)

    # The landscape card has no room for a full-width two-up, and cropping the
    # pair to a squarer box would show the right edge of one image beside the
    # left edge of the other. It gets a single panel instead.
    left.save(out.with_name(out.stem + "_single" + out.suffix))

    print(f"  panel:  {panel.width}x{panel.height} from {len(scored)}/{total} usable")
    print(f"  single: {left.width}x{left.height}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--inspection", help="Inspection id; defaults to the busiest")
    p.add_argument("--full", action="store_true", help="Whole page, not the viewport")
    p.add_argument("--selector", help="CSS selector to capture instead of the page")
    p.add_argument("--panel", action="store_true",
                   help="Build the two-up social-card panel (the usual mode)")
    p.add_argument("--out", help="Output path (default deliverables/dashboard_screenshot.png)")
    args = p.parse_args()

    email = env_value("BOOTSTRAP_ADMIN_EMAIL")
    password = env_value("BOOTSTRAP_ADMIN_PASSWORD")
    if not (email and password):
        sys.exit("set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD in backend/.env")

    out = Path(args.out) if args.out else OUT

    token = login(email, password)
    inspection_id = args.inspection or busiest_inspection(token)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,          # retina, so the card crop stays sharp
            color_scheme="dark",
        )
        # Authenticate through the dashboard's own route so the httpOnly cookie
        # is set exactly as a real sign-in would set it.
        resp = context.request.post(
            f"{DASHBOARD}/api/session",
            data={"email": email, "password": password},
        )
        if not resp.ok:
            sys.exit(f"session route rejected the credentials ({resp.status})")

        page = context.new_page()
        page.goto(f"{DASHBOARD}/inspections/{inspection_id}",
                  wait_until="networkidle", timeout=60_000)

        # The signed-in account's address renders in the header. These images
        # are published, so it is removed before anything is captured — not
        # cropped out afterwards and hoped for. The Next.js dev badge goes too.
        page.add_style_tag(content="""
            nextjs-portal, [data-nextjs-toast] { display: none !important; }
        """)
        page.evaluate("""() => {
            const at = document.evaluate(
                "//*[contains(text(), '@')]", document, null,
                XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
            for (let i = 0; i < at.snapshotLength; i++) {
                const el = at.snapshotItem(i);
                if (el.children.length === 0 && /@[\\w.-]+\\.\\w+/.test(el.textContent)) {
                    el.textContent = "inspector@twinverse.ai";
                }
            }
        }""")

        # Detection overlays only render once the <img> fires onLoad, and an
        # inspection carries dozens of them. "networkidle" is not enough on its
        # own — the first capture caught every media panel blank, boxes and all.
        page.wait_for_function(
            """() => {
                const imgs = [...document.images];
                return imgs.length > 0 && imgs.every(i => i.complete && i.naturalWidth > 0);
            }""",
            timeout=120_000,
        )

        # Entry animations and the counter tweens both run on a timer; without
        # this the stats photograph mid-count and read as zeros. The image fade
        # is 500ms on top of that.
        page.wait_for_timeout(3000)

        if args.panel:
            # The header is sticky and would overlay whichever card is scrolled
            # under it at capture time.
            page.add_style_tag(content="header { position: static !important; }")
            pick_panels(page, out)
        elif args.selector:
            target = page.locator(args.selector).first
            target.scroll_into_view_if_needed()
            page.wait_for_timeout(600)
            target.screenshot(path=str(out))
        else:
            page.screenshot(path=str(out), full_page=args.full)
        browser.close()

    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
