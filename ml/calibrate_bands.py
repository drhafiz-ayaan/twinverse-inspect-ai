#!/usr/bin/env python3
"""Recalibrate the severity band thresholds against a model's actual output.

The bands are percentiles of what the model really produces, not round numbers.
That matters more than it sounds: the original proposal's 0.25 / 0.50 / 0.75 put
**every one** of 308 measured detections into LOW, because a crack's bounding
box covers 2-4% of a frame and the score is that area multiplied by a
confidence below 1.0. See README D-018.

So the thresholds are model-specific. **Swap the checkpoint and they are wrong
again** — a new model with different confidence calibration or box sizes shifts
the whole distribution, and the dashboard silently goes back to reporting one
band for everything.

    python ml/calibrate_bands.py --weights ml/weights/<new>.pt \\
        --images ml/datasets/nitw-crack/test/images

Prints the values to paste into backend/.env, then apply them to already-scored
rows with POST /api/v1/inspections/{id}/rescore — no GPU time needed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

# Percentiles the shipped bands sit at, from D-018. Kept here so a
# recalibration reproduces the same shape rather than inventing a new one.
CUTS = {"medium": 52, "high": 76, "critical": 94}

# The crack weight from backend/app/services/severity.py. A single-class crack
# detector only ever multiplies by this one.
CLASS_WEIGHT = 1.0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--weights", required=True)
    p.add_argument("--images", required=True, help="Directory of images to score")
    p.add_argument("--conf", type=float, default=0.30,
                   help="Detection threshold — must match CONFIDENCE_THRESHOLD")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default="0")
    p.add_argument("--limit", type=int)
    args = p.parse_args()

    image_dir = Path(args.images)
    files = sorted(f for f in image_dir.rglob("*")
                   if f.suffix.lower() in IMAGE_SUFFIXES and f.is_file())
    if args.limit:
        files = files[:args.limit]
    if not files:
        sys.exit(f"no images under {image_dir}")

    from ultralytics import YOLO

    model = YOLO(args.weights)
    scores: list[float] = []

    for start in range(0, len(files), 32):
        batch = files[start:start + 32]
        for result in model.predict(
            [str(f) for f in batch], conf=args.conf, imgsz=args.imgsz,
            device=args.device, verbose=False,
        ):
            h, w = result.orig_shape
            frame = float(h * w)
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                # normalized_area is what the pipeline stores: box area over
                # frame area. Same quantity, so the calibration matches.
                area = ((x2 - x1) * (y2 - y1)) / frame
                scores.append(area * float(box.conf[0]) * CLASS_WEIGHT)

    if not scores:
        sys.exit("the model produced no detections — nothing to calibrate")

    scores.sort()

    def pct(q: int) -> float:
        return scores[min(len(scores) - 1, int(len(scores) * q / 100))]

    print(f"\n{len(scores)} detections over {len(files)} images at conf {args.conf}\n")
    print("  distribution")
    for q in (10, 25, 50, 75, 90, 99):
        print(f"    p{q:<3} {pct(q):.5f}")
    print(f"    max  {scores[-1]:.5f}")

    medium, high, critical = (pct(CUTS[k]) for k in ("medium", "high", "critical"))
    print("\n  paste into backend/.env:\n")
    print(f"    SEVERITY_BAND_MEDIUM={medium:.4f}")
    print(f"    SEVERITY_BAND_HIGH={high:.4f}")
    print(f"    SEVERITY_BAND_CRITICAL={critical:.4f}")

    counts = {
        "low": sum(s < medium for s in scores),
        "medium": sum(medium <= s < high for s in scores),
        "high": sum(high <= s < critical for s in scores),
        "critical": sum(s >= critical for s in scores),
    }
    print("\n  resulting spread")
    for name, n in counts.items():
        print(f"    {name:<9} {n:5d}  {100 * n / len(scores):5.1f}%")

    if scores[-1] < 0.05:
        print("\n  Note: the maximum score is far below 1.0, which is expected —"
              "\n  see README D-018. Do not 'fix' this by using round thresholds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
